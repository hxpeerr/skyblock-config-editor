use std::collections::{BTreeMap, HashMap};
use std::path::Path;
use std::sync::Arc;

use indexmap::IndexMap;
use scm::features::{FeatureSet, Source};
use scm::selfupdate::note_lines;
use scm::text::{fmt, is_debug_segment, make_label, words};
use scm::updates::update_status;
use scm::value::{parse_value, type_name};
use scm::versions::{newer, State};
use scm::workspace::Workspace;
use serde_json::{json, Map, Value};

fn map_arg(text: Option<&String>) -> HashMap<String, String> {
    text.map(|t| serde_json::from_str(t).expect("--priority/--overrides take a JSON object of strings")).unwrap_or_default()
}

fn sorted(m: &HashMap<String, usize>) -> BTreeMap<&String, &usize> {
    m.iter().collect()
}

fn dump(ws: &Workspace) -> Map<String, Value> {
    let folder = ws.folder.clone().unwrap_or_default();
    let rel = |p: &Path| p.strip_prefix(&folder).unwrap_or(p).to_string_lossy().replace('\\', "/");
    let mods: Vec<Value> = ws
        .mods
        .values()
        .map(|m| json!({
            "name": m.name, "auto": m.auto,
            "files": m.files.iter().map(|&f| rel(&ws.files[f].path)).collect::<Vec<_>>(),
            "errors": m.errors.len(), "settings": m.settings.len(), "shared": m.shared,
            "installed": m.installed, "jar": m.jar.as_ref().and_then(|j| j.file_name()).map(|n| n.to_string_lossy().into_owned()),
        }))
        .collect();
    let settings: Vec<Value> = ws
        .settings
        .iter()
        .map(|s| json!({
            "mod": s.mod_name, "key": s.key, "label": s.label, "value": serde_json::to_string(&s.value).unwrap(),
            "locked": s.locked, "rec": s.rec.as_ref().map(|r| serde_json::to_string(r).unwrap()), "shared": s.shared,
            "domain": s.domain, "feature": s.feature.map(|f| ws.features[f].key.clone()), "status": s.status_text(),
        }))
        .collect();
    let features: Vec<Value> = ws
        .features
        .iter()
        .filter(|f| !f.switches.is_empty())
        .map(|f| json!({
            "key": f.key, "winner": f.winner, "live": f.live(),
            "switches": f.switches.iter().map(|(m, us)| (m.clone(), json!(us.iter().map(|&u| ws.settings[u].key.clone()).collect::<Vec<_>>()))).collect::<Map<_, _>>(),
        }))
        .collect();
    let (by_mod, by_area, by_feature) = ws.conflicts();
    let mut out = Map::new();
    out.insert("mods".into(), json!(mods));
    out.insert("settings".into(), json!(settings));
    out.insert("features".into(), json!(features));
    out.insert("shared".into(), json!(ws.shared.iter().map(|&u| format!("{}|{}", ws.settings[u].mod_name, ws.settings[u].key)).collect::<Vec<_>>()));
    out.insert("unique".into(), json!(ws.unique.len()));
    out.insert("choices".into(), json!(ws.choices));
    out.insert("owner".into(), json!(ws.owner.iter().collect::<BTreeMap<_, _>>()));
    out.insert("conflicts".into(), json!({"mod": sorted(&by_mod), "area": sorted(&by_area), "feature": sorted(&by_feature)}));
    out
}

fn state(s: State) -> &'static str {
    match s {
        State::Ok => "ok",
        State::New => "new",
        State::Info => "info",
        State::Missing => "missing",
        State::Failed => "failed",
    }
}

fn text_cases(path: &str) -> Value {
    let cases: Value = serde_json::from_str(&std::fs::read_to_string(path).expect("read cases")).expect("cases are JSON");
    let list = |k: &str| cases[k].as_array().cloned().unwrap_or_default();
    let labels = HashMap::new();
    json!({
        "parse": list("parse").iter().map(|c| match parse_value(c[0].as_str().unwrap(), &c[1]) {
            Ok(v) => json!({"ok": serde_json::to_string(&v).unwrap()}),
            Err(e) => json!({"error": e}),
        }).collect::<Vec<_>>(),
        "fmt": list("fmt").iter().map(|v| fmt(v, 80)).collect::<Vec<_>>(),
        "label": list("label").iter().map(|c| {
            let segs: Vec<String> = c[2].as_array().unwrap().iter().map(|s| s.as_str().unwrap().to_string()).collect();
            make_label(&labels, c[0].as_str().unwrap(), c[1].as_str().unwrap(), &segs)
        }).collect::<Vec<_>>(),
        "debug": list("debug").iter().map(|s| is_debug_segment(s.as_str().unwrap())).collect::<Vec<_>>(),
        "words": list("words").iter().map(|s| words(s.as_str().unwrap())).collect::<Vec<_>>(),
        "type": list("parse").iter().map(|c| type_name(&c[1])).collect::<Vec<_>>(),
        "notes": list("notes").iter().map(|s| json!(note_lines(s.as_str().unwrap()).iter().map(|l| (l.block, &l.spans)).collect::<Vec<_>>())).collect::<Vec<_>>(),
        "newer": list("newer").iter().map(|c| newer(c[0].as_str().unwrap(), c[1].as_str().unwrap())).collect::<Vec<_>>(),
    })
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let opt = |name: &str| args.iter().position(|a| a == name).and_then(|i| args.get(i + 1));
    let flag = |name: &str| args.iter().any(|a| a == name);
    if let Some(path) = opt("--text-cases") {
        println!("{}", text_cases(path));
        return;
    }
    let folder = args.first().expect("usage: scm-dump <config folder> [options]");
    let set = match opt("--features") {
        Some(p) => FeatureSet::parse(&std::fs::read_to_string(p).expect("read --features"), Source::UserFile(p.into())).expect("valid --features"),
        None => FeatureSet::builtin(),
    };
    let gv = opt("--game-version").cloned().unwrap_or_else(|| set.default_game_version.clone());
    let mut ws = Workspace::new(Arc::new(set), map_arg(opt("--priority")), map_arg(opt("--overrides")), &gv);
    if let Err(e) = ws.load(Path::new(folder)) {
        println!("{}", json!({"error": e}));
        return;
    }
    ws.attach_installed();
    let mut out = dump(&ws);
    if flag("--resolve") {
        out.insert("resolved".into(), json!(ws.resolve(None, None)));
        out.insert("after_resolve".into(), json!(dump(&ws)["conflicts"]));
    }
    if flag("--updates") {
        let jars: IndexMap<String, (String, std::path::PathBuf)> = ws
            .mods
            .values()
            .filter_map(|m| Some((m.name.clone(), (m.installed.clone()?, m.jar.clone()?))))
            .collect();
        let result = match update_status(&jars, &ws.game_version, &ws.set) {
            Ok(r) => json!(r.iter().map(|(k, (t, s))| (k.clone(), json!([t, state(*s)]))).collect::<Map<_, _>>()),
            Err(e) => json!({"error": e}),
        };
        out.insert("updates".into(), result);
    }
    if flag("--save") {
        let (saved, errors) = ws.save();
        out.insert("saved".into(), json!(saved));
        out.insert("save_errors".into(), json!(errors.len()));
    }
    println!("{}", serde_json::to_string(&Value::Object(out)).unwrap());
}
