//! "Check for updates" (Modrinth and CurseForge), and downloading the newest mod list.
//!
//! Every address can be overridden with an environment variable, which the tests use to talk to a
//! local stand-in server: SCM_MODRINTH_API, SCM_CFWIDGET, SCM_FEATURES_URL.

use std::collections::HashMap;
use std::fs::File;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::sync::{LazyLock, Mutex};
use std::time::Duration;

use indexmap::IndexMap;
use regex::Regex;
use serde_json::{json, Value};
use sha1::{Digest, Sha1};

use crate::features::FeatureSet;
use crate::fsutil::{stamp, Stamp};
use crate::value::py_str;
use crate::versions::{compare, newer, State};

pub const LOADER: &str = "fabric";
const MODRINTH_API: &str = "https://api.modrinth.com/v2";
/// A public mirror of CurseForge's project pages: CurseForge's own API needs a private key, which an
/// app published with its source can't keep secret.
const CFWIDGET: &str = "https://api.cfwidget.com";
/// Where the newest mod list lives.
pub const FEATURES_URL: &str = "https://raw.githubusercontent.com/hxpeerr/skyblock-config-manager/main/features.jsonc";
const MAX_BODY: u64 = 16 * 1024 * 1024;
const MAX_FEATURES: u64 = 2 * 1024 * 1024;

fn base(var: &str, default: &str) -> String {
    std::env::var(var).ok().filter(|v| !v.is_empty()).unwrap_or_else(|| default.to_string())
}

pub fn features_url() -> String {
    base("SCM_FEATURES_URL", FEATURES_URL)
}

fn agent() -> ureq::Agent {
    ureq::Agent::config_builder()
        .timeout_global(Some(Duration::from_secs(15)))
        .user_agent(format!("skyblock-config-manager/{}", crate::VERSION))
        .build()
        .into()
}

/// A failed request: the HTTP status if the server answered with an error, else what went wrong.
#[derive(Debug)]
pub enum HttpError {
    Status(u16),
    Other(String),
}

impl std::fmt::Display for HttpError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            HttpError::Status(c) => write!(f, "HTTP {c}"),
            HttpError::Other(e) => write!(f, "{e}"),
        }
    }
}

fn from_ureq(e: ureq::Error) -> HttpError {
    match e {
        ureq::Error::StatusCode(c) => HttpError::Status(c),
        other => HttpError::Other(other.to_string()),
    }
}

fn get_text(url: &str, limit: u64) -> Result<String, HttpError> {
    let mut resp = agent().get(url).call().map_err(from_ureq)?;
    resp.body_mut().with_config().limit(limit).read_to_string().map_err(from_ureq)
}

fn get_json(url: &str) -> Result<Value, HttpError> {
    serde_json::from_str(&get_text(url, MAX_BODY)?).map_err(|e| HttpError::Other(e.to_string()))
}

fn post_json(url: &str, body: &Value) -> Result<Value, HttpError> {
    let mut resp = agent()
        .post(url)
        .header("Content-Type", "application/json")
        .send(body.to_string())
        .map_err(from_ureq)?;
    let text = resp.body_mut().with_config().limit(MAX_BODY).read_to_string().map_err(from_ureq)?;
    serde_json::from_str(&text).map_err(|e| HttpError::Other(e.to_string()))
}

/// Percent-encodes everything but letters, digits and `_.-~` (Python's `quote(s, safe="")`).
fn quote(s: &str) -> String {
    s.bytes()
        .map(|b| match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'_' | b'.' | b'-' | b'~' => (b as char).to_string(),
            _ => format!("%{b:02X}"),
        })
        .collect()
}

static SHA1: LazyLock<Mutex<HashMap<PathBuf, (Stamp, String)>>> = LazyLock::new(Default::default);

pub fn sha1_file(path: &Path) -> std::io::Result<String> {
    let st = stamp(path)?;
    if let Some((s, h)) = SHA1.lock().unwrap().get(path) {
        if *s == st {
            return Ok(h.clone());
        }
    }
    let mut f = File::open(path)?;
    let mut hasher = Sha1::new();
    let mut buf = vec![0u8; 1 << 20];
    loop {
        let n = f.read(&mut buf)?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    let digest: String = hasher.finalize().iter().map(|b| format!("{b:02x}")).collect();
    SHA1.lock().unwrap().insert(path.to_path_buf(), (st, digest.clone()));
    Ok(digest)
}

static CF_NAME: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"[-_ ]v?(\d+(?:\.\d+)+\S*)$").unwrap());
static CF_DISPLAY: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(\d+(?:\.\d+)+[\w.+-]*)").unwrap());
static JAR_SUFFIX: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?i)\.jar$").unwrap());

/// The mod version of the newest Fabric file for `game_version` on CurseForge, or None.
pub fn curseforge_latest(project_id: u64, game_version: &str) -> Result<Option<String>, HttpError> {
    let data = get_json(&format!("{}/{project_id}", base("SCM_CFWIDGET", CFWIDGET)))?;
    let loader = "Fabric";
    let has = |f: &Value, what: &str| f.get("versions").and_then(Value::as_array).is_some_and(|vs| vs.iter().any(|v| v == what));
    let files: Vec<&Value> = data
        .get("files")
        .and_then(Value::as_array)
        .map(|fs| fs.iter().filter(|f| f.is_object() && has(f, game_version) && has(f, loader)).collect())
        .unwrap_or_default();
    let uploaded = |f: &Value| f.get("uploaded_at").filter(|v| !v.is_null()).map(py_str).unwrap_or_default();
    let mut newest: Option<&Value> = None;
    for f in files {
        if newest.is_none_or(|n| uploaded(f) > uploaded(n)) {
            newest = Some(f);
        }
    }
    let Some(newest) = newest else { return Ok(None) };
    let name = newest.get("name").filter(|v| !v.is_null()).map(py_str).unwrap_or_default();
    let stem = JAR_SUFFIX.replace(&name, "");
    if let Some(c) = CF_NAME.captures(&stem) {
        return Ok(Some(c[1].to_string()));
    }
    let display = newest.get("display").filter(|v| !v.is_null()).map(py_str).unwrap_or_default();
    Ok(CF_DISPLAY.captures(&display).map(|c| c[1].to_string()))
}

/// Modrinth's answer for one mod.
enum Modrinth {
    /// The installed file is its newest build.
    Current,
    /// Its newest version.
    Newest(String),
    /// No version to compare with: the text and state to show.
    None((String, State)),
}

/// {mod: (text, state)} for installed jars ({mod: (version, jar)}): the newest Fabric build for
/// `game_version` on Modrinth and, for mods also published there, on CurseForge. Whichever is newer
/// is reported. Modrinth is first asked which project each exact file belongs to (by SHA-1), which
/// avoids every naming difference; files it doesn't know fall back to the project slug.
pub fn update_status(jars: &IndexMap<String, (String, PathBuf)>, game_version: &str, set: &FeatureSet)
                     -> Result<IndexMap<String, (String, State)>, String> {
    if jars.is_empty() {
        return Ok(IndexMap::new());
    }
    let mut hashes = IndexMap::new();
    for (name, (_, jar)) in jars {
        hashes.insert(name.clone(), sha1_file(jar).map_err(|e| format!("{}: {e}", jar.display()))?);
    }
    let mut unique: Vec<&String> = hashes.values().collect();
    unique.sort();
    unique.dedup();
    let api = base("SCM_MODRINTH_API", MODRINTH_API);
    let latest = post_json(&format!("{api}/version_files/update"), &json!({
        "hashes": unique, "algorithm": "sha1", "loaders": [LOADER], "game_versions": [game_version]}))
        .map_err(|e| e.to_string())?;

    let mut modrinth: HashMap<&str, Modrinth> = HashMap::new();
    let mut fallback = Vec::new();
    for (name, h) in &hashes {
        let v = latest.get(h.as_str());
        let number = v.and_then(|v| v.get("version_number")).filter(|n| !n.is_null() && *n != "" && *n != false);
        if let (Some(v), Some(number)) = (v.filter(|v| v.is_object()), number) {
            let files: Vec<String> = v
                .get("files")
                .and_then(Value::as_array)
                .map(|fs| fs.iter().filter_map(|f| f.get("hashes")?.get("sha1")?.as_str().map(str::to_string)).collect())
                .unwrap_or_default();
            let number = py_str(number);
            modrinth.insert(name, if files.contains(h) { Modrinth::Current } else { Modrinth::Newest(number) });
        } else if set.mods.get(name).and_then(|m| m.slug.as_ref()).is_some_and(|s| !s.is_empty()) {
            fallback.push(name.as_str());
        } else {
            modrinth.insert(name, Modrinth::None(("not on Modrinth".into(), State::Missing)));
        }
    }

    let query = format!("loaders={}&game_versions={}", quote(&json!([LOADER]).to_string()), quote(&json!([game_version]).to_string()));
    let by_slug = |name: &str| -> Modrinth {
        let slug = quote(set.mods[name].slug.as_deref().unwrap_or_default());
        match get_json(&format!("{api}/project/{slug}/version?{query}")) {
            Ok(Value::Array(vs)) if !vs.is_empty() => match vs[0].get("version_number") {
                Some(n) if !n.is_null() => Modrinth::Newest(py_str(n)),
                _ => Modrinth::None(("check failed".into(), State::Failed)),
            },
            Ok(_) => Modrinth::None((format!("no {game_version} build"), State::Missing)),
            Err(HttpError::Status(404)) => Modrinth::None(("not on Modrinth".into(), State::Missing)),
            Err(HttpError::Status(c)) => Modrinth::None((format!("check failed (HTTP {c})"), State::Failed)),
            Err(HttpError::Other(_)) => Modrinth::None(("check failed".into(), State::Failed)),
        }
    };
    let curse: Vec<(&str, u64)> = jars
        .keys()
        .filter_map(|n| set.mods.get(n).and_then(|m| m.curseforge).map(|id| (n.as_str(), id)))
        .collect();
    let (slug_answers, cf): (Vec<(&str, Modrinth)>, HashMap<&str, String>) = std::thread::scope(|s| {
        let slugs: Vec<_> = fallback.iter().map(|&n| (n, s.spawn(move || by_slug(n)))).collect();
        let cfs: Vec<_> = curse.iter().map(|&(n, id)| (n, s.spawn(move || curseforge_latest(id, game_version)))).collect();
        let slug_answers = slugs.into_iter().map(|(n, h)| (n, h.join().unwrap_or(Modrinth::None(("check failed".into(), State::Failed))))).collect();
        let cf = cfs.into_iter().filter_map(|(n, h)| h.join().ok().and_then(Result::ok).flatten().map(|v| (n, v))).collect();
        (slug_answers, cf)
    });
    modrinth.extend(slug_answers);

    let mut out = IndexMap::new();
    for (name, (installed, _)) in jars {
        let cfv = cf.get(name.as_str());
        let result = match &modrinth[name.as_str()] {
            Modrinth::Current => match cfv {
                Some(c) if newer(c, installed) => (format!("↑ {c} (CurseForge)"), State::New),
                _ => ("up to date".into(), State::Ok),
            },
            Modrinth::Newest(v) => match cfv {
                Some(c) if newer(c, v) => compare(installed, c, "CurseForge"),
                _ => compare(installed, v, "Modrinth"),
            },
            Modrinth::None(value) => match cfv {
                Some(c) => compare(installed, c, "CurseForge"),
                None => value.clone(),
            },
        };
        out.insert(name.clone(), result);
    }
    Ok(out)
}

/// Downloads the newest mod list and checks it. Returns the file's text and what it contains.
pub fn fetch_features() -> Result<(String, FeatureSet), String> {
    let url = features_url();
    let text = get_text(&url, MAX_FEATURES).map_err(|e| e.to_string())?;
    let set = FeatureSet::parse(&text, crate::features::Source::Downloaded(PathBuf::new()))?;
    Ok((text, set))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn quoting() {
        assert_eq!(quote("[\"fabric\"]"), "%5B%22fabric%22%5D");
        assert_eq!(quote("skyblocker-liap"), "skyblocker-liap");
    }
}
