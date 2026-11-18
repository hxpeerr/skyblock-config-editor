//! The mods, features and Minecraft versions the app knows about (features.jsonc).
//!
//! A copy is built into the app. A newer copy downloaded from the repository, or a file the user
//! put next to the app, can replace it; every copy is checked here before it's used, so a broken
//! or unexpected file can't point the app outside the config folder.

use std::collections::{HashMap, HashSet};
use std::path::{Component, Path, PathBuf};

use indexmap::IndexMap;
use serde_json::{Map, Value};

use crate::jsonc::parse_jsonc;

/// The file layout this app understands. Files with a higher "format" are refused.
pub const FORMAT: u64 = 1;
/// The copy built into the app.
pub const BUILTIN: &str = include_str!("../../features.jsonc");

/// One switch, or several switches that always follow together.
#[derive(Clone, Debug, PartialEq)]
pub enum Keys {
    One(String),
    Many(Vec<String>),
}

impl Keys {
    pub fn iter(&self) -> Box<dyn Iterator<Item = &str> + '_> {
        match self {
            Keys::One(k) => Box::new(std::iter::once(k.as_str())),
            Keys::Many(ks) => Box::new(ks.iter().map(String::as_str)),
        }
    }
}

/// How a mod switches a feature on and off.
#[derive(Clone, Debug, PartialEq)]
pub enum SwitchSpec {
    /// The mod has the feature but no single switch for it; it still competes.
    NoSwitch,
    Keys(Keys),
    /// Renamed between Minecraft versions: (version or range, or "other") -> keys, in file order.
    ByVersion(Vec<(String, Keys)>),
}

#[derive(Clone, Debug, PartialEq)]
pub struct ModSpec {
    pub files: Vec<String>,
    pub dir: Option<String>,
    pub id: Option<String>,
    pub slug: Option<String>,
    pub curseforge: Option<u64>,
}

#[derive(Clone, Debug, PartialEq)]
pub struct FeatureSpec {
    pub area: String,
    pub name: String,
    pub mods: Vec<(String, SwitchSpec)>,
}

#[derive(Clone, Debug, PartialEq)]
pub struct Preferred {
    pub mod_name: String,
    pub key: String,
    pub value: Value,
}

#[derive(Clone, Debug, PartialEq)]
pub enum Source {
    BuiltIn,
    Downloaded(PathBuf),
    UserFile(PathBuf),
}

#[derive(Clone, Debug, PartialEq)]
pub struct FeatureSet {
    pub revision: u64,
    pub game_versions: Vec<String>,
    pub default_game_version: String,
    pub mods: IndexMap<String, ModSpec>,
    pub areas: Vec<String>,
    pub features: Vec<FeatureSpec>,
    pub preferred: Vec<Preferred>,
    pub labels: HashMap<(String, String), String>,
    pub source: Source,
}

impl FeatureSet {
    /// The copy built into the app (checked by the tests, so it can't fail at runtime).
    pub fn builtin() -> FeatureSet {
        FeatureSet::parse(BUILTIN, Source::BuiltIn).expect("the built-in features.jsonc is valid")
    }

    /// Reads and checks a features.jsonc.
    pub fn parse(text: &str, source: Source) -> Result<FeatureSet, String> {
        let text = text.strip_prefix('\u{feff}').unwrap_or(text);
        let (value, _) = parse_jsonc(text)?;
        let root = value.as_object().ok_or("the file isn't a JSON object")?;

        let format = uint(root.get("format"), "format")?;
        if format > FORMAT {
            return Err(format!("it's format {format}, which needs a newer version of the app"));
        }
        let revision = uint(root.get("revision"), "revision")?;

        let game_versions = strings(root.get("game_versions"), "game_versions")?;
        if game_versions.is_empty() {
            return Err("game_versions is empty".into());
        }
        let default_game_version = string(root.get("default_game_version"), "default_game_version")?;
        if !game_versions.contains(&default_game_version) {
            return Err("default_game_version isn't one of game_versions".into());
        }

        let mut mods = IndexMap::new();
        for (name, spec) in object(root.get("mods"), "mods")? {
            let at = format!("mods.{name}");
            let spec = spec.as_object().ok_or(format!("{at} isn't an object"))?;
            let files = match spec.get("files") {
                None => Vec::new(),
                v => strings(v, &format!("{at}.files"))?,
            };
            for f in &files {
                safe_path(f, &format!("{at}.files"))?;
            }
            let dir = optional_string(spec.get("dir"), &format!("{at}.dir"))?;
            if let Some(d) = &dir {
                safe_path(d, &format!("{at}.dir"))?;
            }
            let curseforge = match spec.get("curseforge") {
                None | Some(Value::Null) => None,
                v => Some(uint(v, &format!("{at}.curseforge"))?),
            };
            mods.insert(
                name.clone(),
                ModSpec {
                    files,
                    dir,
                    id: optional_string(spec.get("id"), &format!("{at}.id"))?,
                    slug: optional_string(spec.get("slug"), &format!("{at}.slug"))?,
                    curseforge,
                },
            );
        }

        let areas = strings(root.get("areas"), "areas")?;
        if areas.is_empty() || areas.iter().collect::<HashSet<_>>().len() != areas.len() {
            return Err("areas is empty or lists an area twice".into());
        }

        let mut features = Vec::new();
        for (i, f) in array(root.get("features"), "features")?.iter().enumerate() {
            let at = format!("features[{i}]");
            let f = f.as_object().ok_or(format!("{at} isn't an object"))?;
            let area = string(f.get("area"), &format!("{at}.area"))?;
            if !areas.contains(&area) {
                return Err(format!("{at}.area \"{area}\" isn't one of the areas"));
            }
            let name = string(f.get("name"), &format!("{at}.name"))?;
            let mut specs = Vec::new();
            for (mod_name, spec) in object(f.get("mods"), &format!("{at}.mods"))? {
                specs.push((mod_name.clone(), switch_spec(spec, &format!("{at}.mods.{mod_name}"))?));
            }
            features.push(FeatureSpec { area, name, mods: specs });
        }

        let mut preferred = Vec::new();
        for (i, p) in array(root.get("preferred"), "preferred")?.iter().enumerate() {
            let at = format!("preferred[{i}]");
            let p = p.as_object().ok_or(format!("{at} isn't an object"))?;
            preferred.push(Preferred {
                mod_name: string(p.get("mod"), &format!("{at}.mod"))?,
                key: string(p.get("key"), &format!("{at}.key"))?,
                value: p.get("value").cloned().ok_or(format!("{at}.value is missing"))?,
            });
        }

        let mut labels = HashMap::new();
        if let Some(v) = root.get("labels") {
            for (mod_name, keys) in object(Some(v), "labels")? {
                for (key, label) in object(Some(keys), &format!("labels.{mod_name}"))? {
                    let label = label.as_str().ok_or(format!("labels.{mod_name}.{key} isn't a string"))?;
                    labels.insert((mod_name.clone(), key.clone()), label.to_string());
                }
            }
        }

        Ok(FeatureSet {
            revision,
            game_versions,
            default_game_version,
            mods,
            areas,
            features,
            preferred,
            labels,
            source,
        })
    }

    pub fn area_index(&self, area: &str) -> usize {
        self.areas.iter().position(|a| a == area).unwrap_or(self.areas.len())
    }

    /// Where this list came from, for the Activity log.
    pub fn describe(&self) -> String {
        match &self.source {
            Source::BuiltIn => format!("the built-in mod list (revision {})", self.revision),
            Source::Downloaded(_) => format!("the downloaded mod list (revision {})", self.revision),
            Source::UserFile(p) => format!("your mod list at {} (revision {})", p.display(), self.revision),
        }
    }
}

/// Which list to use: a features.jsonc the user put next to the app, else a downloaded copy
/// newer than the built-in one, else the built-in one. Problems are returned as notes.
pub fn choose(user_file: Option<&Path>, cache_file: Option<&Path>) -> (FeatureSet, Vec<String>) {
    let mut notes = Vec::new();
    if let Some(path) = user_file.filter(|p| p.is_file()) {
        match read(path, Source::UserFile(path.to_path_buf())) {
            Ok(set) => return (set, notes),
            Err(e) => notes.push(format!("Ignored {}: {e}", path.display())),
        }
    }
    let builtin = FeatureSet::builtin();
    if let Some(path) = cache_file.filter(|p| p.is_file()) {
        match read(path, Source::Downloaded(path.to_path_buf())) {
            Ok(set) if set.revision > builtin.revision => return (set, notes),
            Ok(_) => {}
            Err(e) => notes.push(format!("Ignored the downloaded mod list ({e}).")),
        }
    }
    (builtin, notes)
}

pub fn read(path: &Path, source: Source) -> Result<FeatureSet, String> {
    let text = std::fs::read_to_string(path).map_err(|e| e.to_string())?;
    FeatureSet::parse(&text, source)
}

// ── checking helpers ──

fn switch_spec(v: &Value, at: &str) -> Result<SwitchSpec, String> {
    match v {
        Value::Null => Ok(SwitchSpec::NoSwitch),
        Value::Object(by_version) => {
            if by_version.is_empty() {
                return Err(format!("{at} is empty"));
            }
            let mut out = Vec::new();
            for (version, keys) in by_version {
                out.push((version.clone(), keys_of(keys, &format!("{at}.{version}"))?));
            }
            Ok(SwitchSpec::ByVersion(out))
        }
        other => Ok(SwitchSpec::Keys(keys_of(other, at)?)),
    }
}

fn keys_of(v: &Value, at: &str) -> Result<Keys, String> {
    match v {
        Value::String(s) if !s.is_empty() => Ok(Keys::One(s.clone())),
        Value::Array(items) if !items.is_empty() => {
            let ks = strings(Some(v), at)?;
            if ks.iter().any(String::is_empty) || ks.len() != items.len() {
                return Err(format!("{at} has an empty key"));
            }
            Ok(Keys::Many(ks))
        }
        _ => Err(format!("{at} must be a key, a list of keys, an object of versions, or null")),
    }
}

/// A path inside the config folder: relative, no "..", no drive letters or streams.
fn safe_path(p: &str, at: &str) -> Result<(), String> {
    let path = Path::new(p);
    let ok = !p.is_empty()
        && !p.contains(':')
        && path.components().all(|c| matches!(c, Component::Normal(_)));
    if ok { Ok(()) } else { Err(format!("{at}: \"{p}\" isn't a path inside the config folder")) }
}

fn uint(v: Option<&Value>, at: &str) -> Result<u64, String> {
    v.and_then(Value::as_u64).ok_or(format!("{at} must be a whole number"))
}

fn string(v: Option<&Value>, at: &str) -> Result<String, String> {
    match v {
        Some(Value::String(s)) if !s.is_empty() => Ok(s.clone()),
        _ => Err(format!("{at} must be text")),
    }
}

fn optional_string(v: Option<&Value>, at: &str) -> Result<Option<String>, String> {
    match v {
        None | Some(Value::Null) => Ok(None),
        Some(Value::String(s)) => Ok(Some(s.clone())),
        _ => Err(format!("{at} must be text")),
    }
}

fn strings(v: Option<&Value>, at: &str) -> Result<Vec<String>, String> {
    array(v, at)?
        .iter()
        .map(|x| x.as_str().map(str::to_string).ok_or(format!("{at} must be a list of text")))
        .collect()
}

fn array<'a>(v: Option<&'a Value>, at: &str) -> Result<&'a Vec<Value>, String> {
    v.and_then(Value::as_array).ok_or(format!("{at} must be a list"))
}

fn object<'a>(v: Option<&'a Value>, at: &str) -> Result<&'a Map<String, Value>, String> {
    v.and_then(Value::as_object).ok_or(format!("{at} must be an object"))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn builtin_is_valid() {
        let set = FeatureSet::builtin();
        assert_eq!(set.features.len(), 83);
        assert_eq!(set.areas.len(), 13);
        assert_eq!(set.mods.len(), 9);
        assert_eq!(set.game_versions.first().map(String::as_str), Some("26.3"));
    }

    #[test]
    fn rejects_paths_outside_the_config_folder() {
        for bad in ["../evil.json", "/etc/x.json", "a/../../b.json", "C:x.json", ""] {
            let text = BUILTIN.replacen("\"NoFrills/Configuration.json\"", &serde_json::to_string(bad).unwrap(), 1);
            assert!(FeatureSet::parse(&text, Source::BuiltIn).is_err(), "{bad} was accepted");
        }
    }

    #[test]
    fn rejects_a_newer_format() {
        let text = BUILTIN.replacen("\"format\": 1", "\"format\": 2", 1);
        assert!(FeatureSet::parse(&text, Source::BuiltIn).unwrap_err().contains("newer version"));
    }

    #[test]
    fn rejects_unknown_areas() {
        let text = BUILTIN.replacen("{\"area\": \"Dungeons\"", "{\"area\": \"Nowhere\"", 1);
        assert!(FeatureSet::parse(&text, Source::BuiltIn).is_err());
    }
}
