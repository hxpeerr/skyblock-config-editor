use std::path::{Path, PathBuf};

use serde_json::{Map, Value};

use crate::features::FeatureSet;
use crate::fsutil::{atomic_write, find_files};

const PORTABLE_PREFS: &str = "skyblock_config_manager.settings.json";
const HOME_PREFS: &str = ".skyblock_config_manager.json";
const PORTABLE_CACHE: &str = "skyblock_config_manager.features.jsonc";
const HOME_CACHE: &str = ".skyblock_config_manager.features.jsonc";
pub const USER_FEATURES: &str = "features.jsonc";
const OLD_AREA_NAMES: &[(&str, &str)] = &[("Garden", "Farming"), ("Diana", "Events"), ("Etherwarp", "Misc")];

pub fn exe_dir() -> Option<PathBuf> {
    std::env::current_exe().ok().and_then(|p| p.parent().map(Path::to_path_buf))
}

pub fn home() -> Option<PathBuf> {
    std::env::home_dir()
}

fn places(portable: &str, in_home: &str) -> Vec<PathBuf> {
    exe_dir().map(|d| d.join(portable)).into_iter().chain(home().map(|h| h.join(in_home))).collect()
}

pub fn prefs_files() -> Vec<PathBuf> {
    places(PORTABLE_PREFS, HOME_PREFS)
}

pub fn feature_cache_files() -> Vec<PathBuf> {
    places(PORTABLE_CACHE, HOME_CACHE)
}

pub fn user_features_file() -> Option<PathBuf> {
    exe_dir().map(|d| d.join(USER_FEATURES))
}

fn renamed_area_key(key: &str) -> String {
    for (old, new) in OLD_AREA_NAMES {
        if let Some(rest) = key.strip_prefix(&format!("{old}/")) {
            return format!("{new}/{rest}");
        }
    }
    key.to_string()
}

pub fn load_prefs() -> Map<String, Value> {
    let mut found: Vec<(std::time::SystemTime, PathBuf)> = prefs_files()
        .into_iter()
        .filter_map(|p| std::fs::metadata(&p).and_then(|m| m.modified()).ok().map(|t| (t, p)))
        .collect();
    found.sort_by(|a, b| b.0.cmp(&a.0));
    for (_, path) in found {
        let Ok(text) = std::fs::read_to_string(&path) else { continue };
        let Ok(Value::Object(mut data)) = serde_json::from_str::<Value>(&text) else { continue };
        if let Some(Value::Object(pr)) = data.get("priority") {
            let renamed: Map<String, Value> = pr
                .iter()
                .filter(|(_, v)| v.is_string())
                .map(|(k, v)| {
                    let k = OLD_AREA_NAMES.iter().find(|(o, _)| o == k).map_or(k.clone(), |(_, n)| n.to_string());
                    (k, v.clone())
                })
                .collect();
            data.insert("priority".into(), Value::Object(renamed));
        }
        if let Some(Value::Object(ov)) = data.get("overrides") {
            let renamed: Map<String, Value> =
                ov.iter().filter(|(_, v)| v.is_string()).map(|(k, v)| (renamed_area_key(k), v.clone())).collect();
            data.insert("overrides".into(), Value::Object(renamed));
        }
        return data;
    }
    Map::new()
}

pub fn save_prefs(prefs: &Map<String, Value>) {
    let text = serde_json::to_string_pretty(&Value::Object(prefs.clone())).unwrap_or_default();
    for path in prefs_files() {
        if atomic_write(&path, &text).is_ok() {
            return;
        }
    }
}

pub fn save_feature_cache(text: &str) -> Option<PathBuf> {
    feature_cache_files().into_iter().find(|p| atomic_write(p, text).is_ok())
}

pub fn feature_cache_file() -> Option<PathBuf> {
    feature_cache_files().into_iter().find(|p| p.is_file())
}

pub fn string_map(prefs: &Map<String, Value>, key: &str) -> std::collections::HashMap<String, String> {
    prefs
        .get(key)
        .and_then(Value::as_object)
        .map(|m| m.iter().filter_map(|(k, v)| v.as_str().map(|s| (k.clone(), s.to_string()))).collect())
        .unwrap_or_default()
}

pub fn detect_config_dir(hints: &[String], set: &FeatureSet) -> Option<PathBuf> {
    let mut cands: Vec<PathBuf> = hints.iter().filter(|h| !h.is_empty()).map(PathBuf::from).collect();
    let mut bases: Vec<PathBuf> = std::env::current_dir().ok().into_iter().collect();
    if let Some(exe) = exe_dir() {
        if let Some(parent) = exe.parent() {
            cands.push(parent.join("config"));
        }
        if !bases.contains(&exe) {
            bases.push(exe);
        }
    }
    for b in bases {
        cands.extend([b.clone(), b.join("config"), b.join("minecraft").join("config"), b.join(".minecraft").join("config")]);
    }
    if let Some(appdata) = std::env::var_os("APPDATA").filter(|v| !v.is_empty()) {
        cands.push(PathBuf::from(appdata).join(".minecraft").join("config"));
    }
    if let Some(h) = home() {
        cands.push(h.join(".minecraft").join("config"));
        cands.push(h.join("Library").join("Application Support").join("minecraft").join("config"));
    }
    cands.into_iter().find(|c| c.is_dir() && set.mods.values().any(|spec| !find_files(c, spec).is_empty()))
}
