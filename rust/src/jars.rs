//! Installed mod jars: what their fabric.mod.json says, and finding Hypixel SkyBlock mods that the
//! mod list doesn't cover.

use std::collections::{HashMap, HashSet};
use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::sync::{Arc, LazyLock, Mutex};

use indexmap::IndexMap;
use regex::Regex;
use serde_json::Value;

use crate::features::FeatureSet;
use crate::fsutil::{has_json_suffix, sorted_entries, stamp, Stamp};
use crate::text::norm;
use crate::value::py_str;
use crate::AUTO_MAX_BYTES;

/// Hypixel's mod API, under both of its ids.
const HYPIXEL_APIS: &[&str] = &["hypixel-mod-api", "hm-api"];
/// Libraries only Hypixel SkyBlock mods use.
const SKYBLOCK_LIBS: &[&str] = &["skyblock-api"];

#[derive(Clone, Debug, PartialEq)]
pub struct JarInfo {
    pub id: String,
    pub version: String,
    pub name: String,
    pub description: String,
    /// Ids it depends on or recommends, lower case.
    pub deps: HashSet<String>,
    /// Names of the jars bundled inside it, lower case.
    pub bundled: Vec<String>,
}

/// jar path -> (stamp, what its fabric.mod.json says), so only changed jars are opened again.
static CACHE: LazyLock<Mutex<HashMap<PathBuf, (Stamp, Option<Arc<JarInfo>>)>>> = LazyLock::new(Default::default);

fn text_of(meta: &serde_json::Map<String, Value>, key: &str) -> Option<String> {
    match meta.get(key) {
        None | Some(Value::Null) => None,
        Some(Value::String(s)) if s.is_empty() => None,
        Some(Value::Bool(false)) => None,
        Some(v) => Some(py_str(v)),
    }
}

fn read_meta(jar: &Path) -> Option<JarInfo> {
    let mut z = zip::ZipArchive::new(fs::File::open(jar).ok()?).ok()?;
    let bundled = z
        .file_names()
        .filter_map(Result::ok)
        .filter(|n| n.starts_with("META-INF/jars/") && n.ends_with(".jar"))
        .map(|n| n.rsplit('/').next().unwrap_or(&n).to_lowercase())
        .collect();
    let mut raw = Vec::new();
    z.by_name("fabric.mod.json").ok()?.read_to_end(&mut raw).ok()?;
    let raw = raw.strip_prefix(b"\xef\xbb\xbf").unwrap_or(&raw);
    let meta: Value = serde_json::from_slice(raw).ok()?;
    let meta = meta.as_object()?;
    let mut deps = HashSet::new();
    for k in ["depends", "recommends"] {
        if let Some(Value::Object(m)) = meta.get(k) {
            deps.extend(m.keys().map(|d| d.to_lowercase()));
        }
    }
    let id = meta.get("id").map(py_str).unwrap_or_default();
    Some(JarInfo {
        version: text_of(meta, "version").unwrap_or_else(|| "?".into()),
        name: text_of(meta, "name").or_else(|| text_of(meta, "id")).unwrap_or_default(),
        description: text_of(meta, "description").unwrap_or_default(),
        id,
        deps,
        bundled,
    })
}

fn jar_meta(jar: &Path, st: Stamp) -> Option<Arc<JarInfo>> {
    if let Some((s, info)) = CACHE.lock().unwrap().get(jar) {
        if *s == st {
            return info.clone();
        }
    }
    let info = read_meta(jar).map(Arc::new);
    CACHE.lock().unwrap().insert(jar.to_path_buf(), (st, info.clone()));
    info
}

/// The mod jars in a folder with what each says about itself, newest file first.
pub fn scan_mods(mods_dir: &Path) -> Vec<(Arc<JarInfo>, PathBuf)> {
    let Ok(rd) = fs::read_dir(mods_dir) else { return Vec::new() };
    let mut jars: Vec<(PathBuf, Stamp)> = rd
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().is_some_and(|e| e.to_string_lossy().to_lowercase() == "jar"))
        .filter_map(|p| stamp(&p).ok().map(|s| (p, s)))
        .collect();
    jars.sort_by(|a, b| b.1 .1.cmp(&a.1 .1)); // newest first if a mod is there twice
    jars.into_iter().filter_map(|(p, s)| jar_meta(&p, s).map(|i| (i, p))).collect()
}

/// {mod name: (version, jar)} for the listed mods, found by the mod id inside each jar.
pub fn installed_jars(mods_dir: &Path, set: &FeatureSet) -> IndexMap<String, (String, PathBuf)> {
    let by_id: HashMap<&str, &str> = set
        .mods
        .iter()
        .filter_map(|(name, spec)| spec.id.as_deref().map(|id| (id, name.as_str())))
        .collect();
    let mut found = IndexMap::new();
    for (info, jar) in scan_mods(mods_dir) {
        if let Some(name) = by_id.get(info.id.as_str()) {
            found.entry(name.to_string()).or_insert((info.version.clone(), jar));
        }
    }
    found
}

/// Is this a Hypixel SkyBlock mod? It must say it's for SkyBlock and either name Hypixel or use
/// Hypixel's mod API, or be built on a SkyBlock-only library. That keeps out Hypixel mods for other
/// games and the unrelated sky-island survival mods also called "skyblock".
pub fn is_skyblock_mod(info: &JarInfo) -> bool {
    let text = format!("{} {} {}", info.id, info.name, info.description).to_lowercase();
    let uses = |ids: &[&str]| ids.iter().any(|i| info.deps.contains(*i) || info.bundled.iter().any(|b| b.starts_with(i)));
    let skyblock = text.contains("skyblock") || text.contains("sky block");
    (skyblock && (text.contains("hypixel") || uses(HYPIXEL_APIS))) || uses(SKYBLOCK_LIBS)
}

/// A Hypixel SkyBlock mod the mod list doesn't cover, with the config files named after it.
#[derive(Clone, Debug)]
pub struct FoundMod {
    pub paths: Vec<PathBuf>,
    pub id: String,
    pub jar: PathBuf,
    pub version: String,
}

static SKIP: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?i)cache|backup|\.bak").unwrap());

/// {name: found mod} for Hypixel SkyBlock mods in the mods folder that the list doesn't have, with
/// the JSON files in the config folder named after them (or in a folder named after them).
pub fn discover_mods(config_dir: &Path, claimed: &HashSet<PathBuf>, set: &FeatureSet) -> IndexMap<String, FoundMod> {
    let mut found = IndexMap::new();
    let Ok(entries) = sorted_entries(config_dir) else { return found };
    let mut known: HashSet<String> = set.mods.values().filter_map(|s| s.id.clone()).collect();
    let mut taken: HashSet<String> = set.mods.keys().cloned().collect();
    let mods_dir = config_dir.parent().map(|p| p.join("mods")).unwrap_or_else(|| PathBuf::from("mods"));
    for (info, jar) in scan_mods(&mods_dir) {
        if known.contains(&info.id) || !is_skyblock_mod(&info) {
            continue;
        }
        known.insert(info.id.clone()); // an older copy of the same mod is skipped
        let names: HashSet<String> = [norm(&info.id), norm(&info.name)].into_iter().filter(|n| !n.is_empty()).collect();
        let mut wanted = names.clone();
        for n in &names {
            for suffix in ["config", "client", "settings"] {
                wanted.insert(format!("{n}{suffix}"));
            }
        }
        let mut paths = Vec::new();
        for entry in &entries {
            let file_name = entry.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
            let is_file = entry.is_file();
            let base = if is_file { file_name.split('.').next().unwrap_or("").to_string() } else { file_name };
            if !wanted.contains(&norm(&base)) {
                continue;
            }
            let inside = if entry.is_dir() {
                match sorted_entries(entry) {
                    Ok(v) => v,
                    Err(_) => continue,
                }
            } else {
                vec![entry.clone()]
            };
            for path in inside {
                let name = path.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
                if path.is_file()
                    && has_json_suffix(&path)
                    && !claimed.contains(&path)
                    && !SKIP.is_match(&name)
                    && fs::metadata(&path).is_ok_and(|m| m.len() <= AUTO_MAX_BYTES)
                {
                    paths.push(path);
                }
            }
        }
        if !paths.is_empty() {
            let mut name = if info.name.is_empty() { info.id.clone() } else { info.name.clone() };
            while taken.contains(&name) {
                name.push_str(" (found)");
            }
            taken.insert(name.clone());
            found.insert(name, FoundMod { paths, id: info.id.clone(), jar, version: info.version.clone() });
        }
    }
    found
}
