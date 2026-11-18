use std::cmp::Ordering;
use std::sync::LazyLock;

use regex::Regex;

use crate::features::{Keys, SwitchSpec};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Num(String);

impl Num {
    fn new(digits: &str) -> Num {
        let t = digits.trim_start_matches('0');
        Num(if t.is_empty() { "0".into() } else { t.into() })
    }
}

impl Ord for Num {
    fn cmp(&self, other: &Self) -> Ordering {
        self.0.len().cmp(&other.0.len()).then_with(|| self.0.cmp(&other.0))
    }
}

impl PartialOrd for Num {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

static DIGITS: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\d+").unwrap());

fn numbers(s: &str) -> Vec<Num> {
    DIGITS.find_iter(s).map(|m| Num::new(m.as_str())).collect()
}

pub fn vtuple(v: &str) -> Vec<Num> {
    numbers(v)
}

pub fn version_in(version: &str, spec: &str) -> bool {
    let (lo, hi) = spec.split_once('-').unwrap_or((spec, ""));
    let hi = if hi.is_empty() { lo } else { hi };
    let v = vtuple(version);
    vtuple(lo) <= v && v <= vtuple(hi)
}

pub fn switch_names<'a>(spec: &'a SwitchSpec, version: &str) -> Vec<&'a Keys> {
    match spec {
        SwitchSpec::NoSwitch => Vec::new(),
        SwitchSpec::Keys(k) => vec![k],
        SwitchSpec::ByVersion(by) => {
            let picked = by.iter().position(|(v, _)| v != "other" && version_in(version, v)).or_else(|| by.iter().position(|(v, _)| v == "other"));
            let mut out: Vec<&Keys> = picked.map(|i| &by[i].1).into_iter().collect();
            out.extend(by.iter().enumerate().filter(|(i, _)| Some(*i) != picked).map(|(_, (_, k))| k));
            out
        }
    }
}

static MC_SUFFIX: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"[-_](?:mc-?)?(?:1\.\d{2}|\d{2}\.\d+)(?:\.(?:\d+|x))*$").unwrap());
static LEAD: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"^(\d+(?:\.\d+)*)(.*)$").unwrap());

pub fn version_core(v: &str) -> String {
    let v = v.trim().to_lowercase();
    let v = v.strip_prefix('v').unwrap_or(&v);
    let v = v.split('+').next().unwrap_or("");
    MC_SUFFIX.replace_all(v, "").into_owned()
}

pub fn version_key(v: &str) -> Option<(Vec<Num>, Vec<Num>)> {
    let core = version_core(v);
    let caps = LEAD.captures(&core)?;
    let mut main = numbers(&caps[1]);
    while main.len() < 4 {
        main.push(Num::new("0"));
    }
    let rest = &caps[2];
    let pre = if rest.is_empty() {
        vec![Num::new("1")]
    } else {
        std::iter::once(Num::new("0")).chain(numbers(rest)).collect()
    };
    Some((main, pre))
}

pub fn newer(a: &str, b: &str) -> bool {
    matches!((version_key(a), version_key(b)), (Some(ka), Some(kb)) if ka > kb)
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum State {
    Ok,
    New,
    Info,
    Missing,
    Failed,
}

pub fn compare(installed: &str, latest: &str, source: &str) -> (String, State) {
    let at = if source == "Modrinth" { String::new() } else { format!(" ({source})") };
    match (version_key(installed), version_key(latest)) {
        (Some(a), Some(b)) => {
            if b > a { (format!("↑ {latest}{at}"), State::New) } else { ("up to date".into(), State::Ok) }
        }
        _ if version_core(installed) != version_core(latest) => (format!("{source}: {latest}"), State::Info),
        _ => ("up to date".into(), State::Ok),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn minecraft_versions() {
        assert!(version_in("1.21.8", "1.21.5-1.21.10"));
        assert!(!version_in("26.1", "1.21.5-1.21.11"));
        assert!(version_in("1.21.7", "1.21.7"));
        let by = SwitchSpec::ByVersion(vec![("1.21.5-1.21.10".into(), Keys::One("old".into())), ("other".into(), Keys::One("new".into()))]);
        assert_eq!(switch_names(&by, "1.21.8"), [&Keys::One("old".into()), &Keys::One("new".into())]);
        assert_eq!(switch_names(&by, "26.1.2"), [&Keys::One("new".into()), &Keys::One("old".into())]);
    }

    #[test]
    fn mod_versions() {
        assert_eq!(version_core("v6.11.0+26.1.2"), "6.11.0");
        assert_eq!(version_core("44.3.0+mc26.1"), "44.3.0");
        assert_eq!(version_core("0.7.2-beta.3-26.1.X"), "0.7.2-beta.3");
        assert_eq!(version_core("1.4.2-mc1.21.10"), "1.4.2");
        assert!(newer("6.12.0", "6.11.0+26.1.2"));
        assert!(newer("1.0.0", "1.0.0-beta.2"));
        assert!(!newer("1.0.0", "1.0.0"));
        assert_eq!(compare("1.0", "1.1", "CurseForge").0, "↑ 1.1 (CurseForge)");
        assert_eq!(compare("abc", "def", "Modrinth"), ("Modrinth: def".into(), State::Info));
    }
}
