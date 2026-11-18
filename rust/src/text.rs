use std::collections::HashMap;

use serde_json::Value;

use crate::jsonc::compact_preview;

const ACRONYMS: &[&str] = &["ui", "hud", "esp", "gui", "api", "fps", "hp", "xp", "id", "npc", "uuid", "url", "rgb",
                            "fov", "ah", "bz", "tps", "pvp", "bin"];
const MINOR: &[&str] = &["and", "or", "of", "the", "in", "on", "to", "for", "a", "an"];
const GENERIC: &[&str] = &["enabled", "enable", "toggle", "active", "state", "on", "value"];
const CONTAINERS: &[&str] = &["position", "pos", "offset", "color", "colour", "size", "scale"];

const DEBUG_WORDS: &[&str] = &["debug", "debugs", "debugging", "debugger", "dev", "devs", "developer", "developers",
                               "devmode", "devtool", "devtools"];
const DEBUG_FILLER: &[&str] = &["mode", "modes", "enabled", "enable", "toggle", "toggled", "on", "active", "value",
                                "show", "info", "log", "logs", "logging", "logger", "message", "messages", "output",
                                "print", "verbose", "tool", "tools", "option", "options", "setting", "settings",
                                "config", "feature", "features", "only"];

pub fn norm(text: &str) -> String {
    text.to_lowercase().chars().filter(|c| c.is_ascii_lowercase() || c.is_ascii_digit()).collect()
}

pub fn split_words(segment: &str) -> Vec<String> {
    let chars: Vec<char> = segment.chars().collect();
    let (mut out, mut cur) = (Vec::new(), String::new());
    let lowd = |c: char| c.is_ascii_lowercase() || c.is_ascii_digit();
    for (i, &c) in chars.iter().enumerate() {
        if c == '_' || c == '-' || c.is_whitespace() {
            if !cur.is_empty() {
                out.push(std::mem::take(&mut cur));
            }
            continue;
        }
        if i > 0 && !cur.is_empty() {
            let prev = chars[i - 1];
            let next_lower = chars.get(i + 1).is_some_and(|n| n.is_ascii_lowercase());
            if (lowd(prev) && c.is_ascii_uppercase()) || (prev.is_ascii_uppercase() && c.is_ascii_uppercase() && next_lower) {
                out.push(std::mem::take(&mut cur));
            }
        }
        cur.push(c);
    }
    if !cur.is_empty() {
        out.push(cur);
    }
    out
}

fn is_upper(s: &str) -> bool {
    let mut cased = false;
    for c in s.chars() {
        if c.is_lowercase() {
            return false;
        }
        cased |= c.is_uppercase();
    }
    cased
}

pub fn words(segment: &str) -> String {
    let mut out: Vec<String> = Vec::new();
    for w in split_words(segment) {
        let low = w.to_lowercase();
        if ACRONYMS.contains(&low.as_str()) {
            out.push(low.to_uppercase());
        } else if !out.is_empty() && MINOR.contains(&low.as_str()) {
            out.push(low);
        } else if is_upper(&w) && w.chars().count() > 1 {
            out.push(w);
        } else {
            let mut cs = w.chars();
            let first = cs.next().map(|c| c.to_uppercase().collect::<String>()).unwrap_or_default();
            out.push(first + cs.as_str());
        }
    }
    if out.is_empty() { segment.to_string() } else { out.join(" ") }
}

pub fn make_label(labels: &HashMap<(String, String), String>, mod_name: &str, key: &str, segments: &[String]) -> String {
    if let Some(l) = labels.get(&(mod_name.to_string(), key.to_string())) {
        return l.clone();
    }
    let leaf = segments.last().map(String::as_str).unwrap_or("");
    let parent = if segments.len() > 1 { segments[segments.len() - 2].as_str() } else { "" };
    if !parent.is_empty() && GENERIC.contains(&leaf.to_lowercase().as_str()) {
        return words(parent);
    }
    if !parent.is_empty() && norm(parent) != norm(leaf) {
        if segments.len() > 2 && CONTAINERS.contains(&parent.to_lowercase().as_str()) {
            return format!("{} › {} › {}", words(&segments[segments.len() - 3]), words(parent), words(leaf));
        }
        return format!("{} › {}", words(parent), words(leaf));
    }
    words(leaf)
}

pub fn is_debug_segment(segment: &str) -> bool {
    let found: Vec<String> = split_words(segment).iter().map(|w| w.to_lowercase()).collect();
    found.iter().any(|w| DEBUG_WORDS.contains(&w.as_str()))
        && found.iter().all(|w| DEBUG_WORDS.contains(&w.as_str()) || DEBUG_FILLER.contains(&w.as_str()))
}

pub fn is_debug(segments: &[String]) -> bool {
    segments.iter().any(|s| is_debug_segment(s))
}

pub fn fmt(value: &Value, limit: usize) -> String {
    let text = match value {
        Value::Null => return "—".into(),
        Value::Bool(b) => return (if *b { "true" } else { "false" }).into(),
        Value::Array(_) | Value::Object(_) => compact_preview(value, limit).0,
        Value::Number(n) => n.to_string(),
        Value::String(s) => s.clone(),
    };
    if text.chars().count() <= limit {
        text
    } else {
        text.chars().take(limit - 1).chain(std::iter::once('…')).collect()
    }
}

pub fn plural(n: usize, word: &str) -> String {
    format!("{n} {word}{}", if n == 1 { "" } else { "s" })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn labels() {
        assert_eq!(words("enableTeleportOverlays"), "Enable Teleport Overlays");
        assert_eq!(words("etherwarp-overlay"), "Etherwarp Overlay");
        assert_eq!(words("DUNGEONS_MAP_DISPLAY"), "DUNGEONS MAP DISPLAY");
        assert_eq!(words("hideGuiInDebugMenu"), "Hide GUI in Debug Menu");
        assert_eq!(words("HTMLParser"), "HTML Parser");
        let none = HashMap::new();
        let seg = |s: &[&str]| s.iter().map(|x| x.to_string()).collect::<Vec<_>>();
        assert_eq!(make_label(&none, "M", "a.b", &seg(&["dungeonMap", "enabled"])), "Dungeon Map");
        assert_eq!(make_label(&none, "M", "a.b.c", &seg(&["map", "position", "x"])), "Map › Position › X");
        assert_eq!(make_label(&none, "M", "a.b", &seg(&["gui", "hideGuiInDebugMenu"])), "GUI › Hide GUI in Debug Menu");
    }

    #[test]
    fn debug_rule() {
        for s in ["dev", "debug", "devTool", "debugMode", "DEVELOPER_MODE", "Developer Message", "debugOnlyMessages"] {
            assert!(is_debug_segment(s), "{s}");
        }
        for s in ["hideGuiInDebugMenu", "debugHud", "extraDebugInfo", "developer-capes", "Dev Size", "device", "mode"] {
            assert!(!is_debug_segment(s), "{s}");
        }
    }

    #[test]
    fn previews() {
        assert_eq!(fmt(&Value::Null, 80), "—");
        assert_eq!(fmt(&serde_json::json!("x".repeat(100)), 10), format!("{}…", "x".repeat(9)));
        assert_eq!(fmt(&serde_json::json!([1, 2]), 80), "[1,2]");
    }
}
