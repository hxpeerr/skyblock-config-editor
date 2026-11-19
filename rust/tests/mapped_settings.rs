use std::collections::{BTreeMap, HashMap};
use std::fs;
use std::path::Path;
use std::sync::Arc;

use scm::features::{FeatureSet, SwitchSpec};
use scm::versions::switch_names;
use scm::workspace::Workspace;
use serde_json::{Map, Value};

fn every_key(spec: &SwitchSpec) -> Vec<String> {
    match spec {
        SwitchSpec::NoSwitch => Vec::new(),
        SwitchSpec::Keys(k) => k.iter().map(str::to_string).collect(),
        SwitchSpec::ByVersion(by) => by.iter().flat_map(|(_, k)| k.iter().map(str::to_string)).collect(),
    }
}

fn put(tree: &mut Map<String, Value>, path: &[&str]) -> Result<(), String> {
    let clash = || format!("{} is both an on/off setting and a group of settings", path.join("."));
    let (last, parents) = path.split_last().ok_or_else(clash)?;
    let mut node = tree;
    for p in parents {
        node = node.entry(p.to_string()).or_insert_with(|| Value::Object(Map::new())).as_object_mut().ok_or_else(clash)?;
    }
    if node.get(*last).is_some_and(Value::is_object) {
        return Err(clash());
    }
    node.insert(last.to_string(), Value::Bool(true));
    Ok(())
}

fn segments(key: &str) -> Vec<&str> {
    match key.strip_prefix('*') {
        Some(tail) => std::iter::once("features").chain(tail.split('.')).collect(),
        None => key.split('.').collect(),
    }
}

fn write(path: &Path, value: Value) {
    fs::create_dir_all(path.parent().unwrap()).unwrap();
    fs::write(path, serde_json::to_string_pretty(&value).unwrap()).unwrap();
}

fn write_configs(set: &FeatureSet, root: &Path) -> Vec<String> {
    let mut problems = Vec::new();
    for (name, spec) in &set.mods {
        let keys: Vec<String> = set
            .features
            .iter()
            .flat_map(|f| f.mods.iter().filter(|(m, _)| m == name).flat_map(|(_, s)| every_key(s)))
            .collect();
        if keys.is_empty() {
            continue;
        }
        if let Some(dir) = &spec.dir {
            let mut files: BTreeMap<String, Map<String, Value>> = BTreeMap::new();
            for key in &keys {
                let Some((stem, rest)) = key.split_once('.') else {
                    problems.push(format!("{name}: {key} doesn't start with the name of a file in {dir}"));
                    continue;
                };
                if let Err(e) = put(files.entry(stem.to_string()).or_default(), &segments(rest)) {
                    problems.push(format!("{name}: {e}"));
                }
            }
            for (stem, tree) in files {
                write(&root.join(dir).join(format!("{stem}.json")), Value::Object(tree));
            }
        } else if name == "Odin" {
            let mut modules: BTreeMap<String, Map<String, Value>> = BTreeMap::new();
            for key in &keys {
                let Some((module, rest)) = key.split_once('.') else {
                    problems.push(format!("{name}: {key} doesn't start with a module name"));
                    continue;
                };
                let entry = modules.entry(module.to_string()).or_insert_with(|| {
                    let mut m = Map::new();
                    m.insert("name".into(), Value::String(module.to_string()));
                    m
                });
                if let Err(e) = put(entry, &segments(rest)) {
                    problems.push(format!("{name}: {e}"));
                }
            }
            write(&root.join(&spec.files[0]), Value::Array(modules.into_values().map(Value::Object).collect()));
        } else {
            let mut tree = Map::new();
            if keys.iter().any(|key| put(&mut tree, &segments(key)).is_err()) {
                tree = Map::new();
                for key in &keys {
                    let path = match key.strip_prefix('*') {
                        Some(tail) => vec!["features", tail],
                        None => vec![key.as_str()],
                    };
                    if let Err(e) = put(&mut tree, &path) {
                        problems.push(format!("{name}: {e}"));
                    }
                }
            }
            write(&root.join(&spec.files[0]), Value::Object(tree));
        }
    }
    problems
}

#[test]
fn every_mapped_setting_is_found() {
    let set = Arc::new(FeatureSet::builtin());
    let dir = tempfile::tempdir().unwrap();
    let mut problems = write_configs(&set, dir.path());
    for version in &set.game_versions {
        let mut ws = Workspace::new(Arc::clone(&set), HashMap::new(), HashMap::new(), version);
        ws.load(dir.path()).unwrap();
        for (spec, feature) in set.features.iter().zip(&ws.features) {
            for (name, switch) in &spec.mods {
                if matches!(switch, SwitchSpec::NoSwitch) {
                    continue;
                }
                let wanted = switch_names(switch, version).first().map_or(0, |k| k.iter().count());
                let found = feature.switches.get(name).map_or(0, Vec::len);
                if found < wanted {
                    problems.push(format!("Minecraft {version}: {} / {} / {name}: the app found {found} of {wanted} on/off settings", spec.area, spec.name));
                }
            }
        }
    }
    problems.sort();
    problems.dedup();
    assert!(problems.is_empty(), "{} problems:\n{}", problems.len(), problems.join("\n"));
}
