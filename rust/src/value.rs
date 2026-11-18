use serde_json::{Number, Value};

use crate::jsonc::py_float_repr;

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum Seg {
    Key(String),
    Index(usize),
}

pub fn is_int(n: &Number) -> bool {
    !n.to_string().contains(['.', 'e', 'E'])
}

pub fn type_name(v: &Value) -> &'static str {
    match v {
        Value::Null => "NoneType",
        Value::Bool(_) => "bool",
        Value::Number(n) if is_int(n) => "int",
        Value::Number(_) => "float",
        Value::String(_) => "str",
        Value::Array(_) => "list",
        Value::Object(_) => "dict",
    }
}

pub fn py_str(v: &Value) -> String {
    match v {
        Value::String(s) => s.clone(),
        Value::Bool(true) => "True".into(),
        Value::Bool(false) => "False".into(),
        Value::Null => "None".into(),
        Value::Number(n) => n.to_string(),
        other => serde_json::to_string(other).unwrap_or_default(),
    }
}

pub fn leaves(root: &Value) -> Vec<(Vec<Seg>, Vec<String>, &Value)> {
    let mut out = Vec::new();
    let mut stack: Vec<(&Value, Vec<Seg>, Vec<String>)> = vec![(root, Vec::new(), Vec::new())];
    while let Some((node, path, shown)) = stack.pop() {
        match node {
            Value::Object(map) => {
                for (k, v) in map.iter().rev() {
                    let (mut p, mut s) = (path.clone(), shown.clone());
                    p.push(Seg::Key(k.clone()));
                    s.push(k.clone());
                    stack.push((v, p, s));
                }
            }
            Value::Array(items) if !items.is_empty() && items.iter().all(|x| x.get("name").is_some() && x.is_object()) => {
                let mut kids = Vec::new();
                for (i, item) in items.iter().enumerate() {
                    let map = item.as_object().expect("checked above");
                    let name = py_str(&map["name"]);
                    for (k, v) in map.iter().filter(|(k, _)| k.as_str() != "name") {
                        let (mut p, mut s) = (path.clone(), shown.clone());
                        p.push(Seg::Index(i));
                        p.push(Seg::Key(k.clone()));
                        s.push(name.clone());
                        s.push(k.clone());
                        kids.push((v, p, s));
                    }
                }
                stack.extend(kids.into_iter().rev());
            }
            Value::Null => {}
            _ => out.push((path, shown, node)),
        }
    }
    out
}

pub fn node_mut<'a>(mut v: &'a mut Value, path: &[Seg]) -> Option<&'a mut Value> {
    for seg in path {
        v = match seg {
            Seg::Key(k) => v.as_object_mut()?.get_mut(k)?,
            Seg::Index(i) => v.as_array_mut()?.get_mut(*i)?,
        };
    }
    Some(v)
}

pub fn parse_value(text: &str, old: &Value) -> Result<Value, String> {
    let t = text.trim();
    match old {
        Value::Bool(_) => match t.to_lowercase().as_str() {
            "true" | "1" | "yes" | "on" => Ok(Value::Bool(true)),
            "false" | "0" | "no" | "off" => Ok(Value::Bool(false)),
            _ => Err("Enter true or false.".into()),
        },
        Value::Number(n) if is_int(n) => parse_int(t).ok_or_else(|| "Enter a whole number.".to_string()),
        Value::Number(_) => {
            let clean = without_digit_underscores(t).ok_or("Enter a number.")?;
            let x: f64 = clean.parse().map_err(|_| "Enter a number.")?;
            if !x.is_finite() {
                return Err("Enter a finite number.".into());
            }
            number(&py_float_repr(x))
        }
        Value::Array(_) | Value::Object(_) => {
            let v: Value = serde_json::from_str(t).map_err(|e| format!("Not valid JSON: {e}"))?;
            match (old, &v) {
                (Value::Array(_), Value::Array(_)) | (Value::Object(_), Value::Object(_)) => Ok(v),
                (Value::Array(_), _) => Err("Enter a JSON list.".into()),
                _ => Err("Enter a JSON object.".into()),
            }
        }
        _ => Ok(Value::String(text.to_string())),
    }
}

fn parse_int(t: &str) -> Option<Value> {
    let (neg, digits) = match t.strip_prefix('-') {
        Some(rest) => (true, rest),
        None => (false, t.strip_prefix('+').unwrap_or(t)),
    };
    let clean = without_digit_underscores(digits)?;
    if clean.is_empty() || !clean.chars().all(|c| c.is_ascii_digit()) {
        return None;
    }
    let trimmed = clean.trim_start_matches('0');
    let body = if trimmed.is_empty() { "0" } else { trimmed };
    let text = if neg && body != "0" { format!("-{body}") } else { body.to_string() };
    number(&text).ok()
}

fn without_digit_underscores(t: &str) -> Option<String> {
    let b = t.as_bytes();
    for (i, &c) in b.iter().enumerate() {
        if c == b'_' && !(i > 0 && b[i - 1].is_ascii_digit() && b.get(i + 1).is_some_and(u8::is_ascii_digit)) {
            return None;
        }
    }
    Some(t.replace('_', ""))
}

fn number(text: &str) -> Result<Value, String> {
    serde_json::from_str::<Number>(text).map(Value::Number).map_err(|e| e.to_string())
}

pub fn same(a: &Value, b: &Value) -> bool {
    if a.is_boolean() || b.is_boolean() {
        return a == b;
    }
    py_eq(a, b)
}

pub fn py_eq(a: &Value, b: &Value) -> bool {
    fn num(v: &Value) -> Option<f64> {
        match v {
            Value::Number(n) => n.to_string().parse().ok(),
            Value::Bool(b) => Some(if *b { 1.0 } else { 0.0 }),
            _ => None,
        }
    }
    match (a, b) {
        (Value::Number(x), Value::Number(y)) if is_int(x) && is_int(y) => x.to_string() == y.to_string(),
        (Value::Number(_) | Value::Bool(_), Value::Number(_) | Value::Bool(_)) => num(a) == num(b),
        (Value::Array(x), Value::Array(y)) => x.len() == y.len() && x.iter().zip(y).all(|(p, q)| py_eq(p, q)),
        (Value::Object(x), Value::Object(y)) => {
            x.len() == y.len() && x.iter().all(|(k, v)| y.get(k).is_some_and(|w| py_eq(v, w)))
        }
        _ => a == b,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn walks_named_lists_by_name() {
        let v = json!({"a": {"b": true, "n": null}, "mods": [{"name": "Map", "enabled": true}], "l": [1, 2]});
        let got: Vec<String> = leaves(&v).iter().map(|(_, s, _)| s.join(".")).collect();
        assert_eq!(got, ["a.b", "mods.Map.enabled", "l"]);
        assert_eq!(leaves(&v)[1].0, vec![Seg::Key("mods".into()), Seg::Index(0), Seg::Key("enabled".into())]);
    }

    #[test]
    fn typed_input() {
        assert_eq!(parse_value(" Yes ", &json!(false)).unwrap(), json!(true));
        assert!(parse_value("maybe", &json!(false)).is_err());
        assert_eq!(parse_value("1_000", &json!(5)).unwrap().to_string(), "1000");
        assert_eq!(parse_value("-007", &json!(5)).unwrap().to_string(), "-7");
        assert!(parse_value("1.5", &json!(5)).is_err());
        assert_eq!(parse_value("1e-5", &json!(0.5)).unwrap().to_string(), "1e-05");
        assert_eq!(parse_value("3", &json!(0.5)).unwrap().to_string(), "3.0");
        assert_eq!(parse_value("inf", &json!(0.5)).unwrap_err(), "Enter a finite number.");
        assert_eq!(parse_value("{}", &json!([1])).unwrap_err(), "Enter a JSON list.");
        assert_eq!(parse_value("  keep  ", &json!("s")).unwrap(), json!("  keep  "));
    }

    #[test]
    fn equality() {
        assert!(!same(&json!(true), &json!(1)));
        assert!(same(&json!(1), &serde_json::from_str::<Value>("1.0").unwrap()));
        assert!(py_eq(&json!([true]), &json!([1])));
    }
}
