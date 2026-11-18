use std::io::{self, Write};

use serde::Serialize;
use serde_json::Value;

pub fn parse_jsonc(text: &str) -> Result<(Value, bool), String> {
    if let Ok(v) = serde_json::from_str::<Value>(text) {
        return Ok((v, false));
    }
    let (clean, found) = strip_comments(text);
    let clean = strip_trailing_commas(&clean);
    serde_json::from_str::<Value>(&clean).map(|v| (v, found)).map_err(|e| e.to_string())
}

fn string_len(b: &[u8], start: usize) -> Option<usize> {
    let mut j = start + 1;
    while j < b.len() {
        match b[j] {
            b'\\' => j += 2,
            b'"' => return Some(j + 1 - start),
            _ => j += 1,
        }
    }
    None
}

fn strip_comments(text: &str) -> (String, bool) {
    let b = text.as_bytes();
    let mut out = String::with_capacity(text.len());
    let (mut i, mut last, mut found) = (0, 0, false);
    let blank = |out: &mut String, s: &str| out.extend(s.chars().map(|c| if c == '\n' { '\n' } else { ' ' }));
    while i < b.len() {
        match b[i] {
            b'"' => match string_len(b, i) {
                Some(n) => i += n,
                None => i += 1,
            },
            b'/' if b.get(i + 1) == Some(&b'/') => {
                let end = text[i..].find('\n').map_or(b.len(), |n| i + n);
                out.push_str(&text[last..i]);
                blank(&mut out, &text[i..end]);
                found = true;
                i = end;
                last = end;
            }
            b'/' if b.get(i + 1) == Some(&b'*') => match text[i + 2..].find("*/") {
                Some(n) => {
                    let end = i + 2 + n + 2;
                    out.push_str(&text[last..i]);
                    blank(&mut out, &text[i..end]);
                    found = true;
                    i = end;
                    last = end;
                }
                None => i += 1,
            },
            _ => i += 1,
        }
    }
    out.push_str(&text[last..]);
    (out, found)
}

fn strip_trailing_commas(text: &str) -> String {
    let b = text.as_bytes();
    let mut out = String::with_capacity(text.len());
    let (mut i, mut last) = (0, 0);
    while i < b.len() {
        match b[i] {
            b'"' => match string_len(b, i) {
                Some(n) => i += n,
                None => i += 1,
            },
            b',' => {
                let rest = &text[i + 1..];
                let after = rest.trim_start_matches(char::is_whitespace);
                if after.starts_with('}') || after.starts_with(']') {
                    out.push_str(&text[last..i]);
                    i += 1;
                    last = i;
                } else {
                    i += 1;
                }
            }
            _ => i += 1,
        }
    }
    out.push_str(&text[last..]);
    out
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Indent {
    OneLine,
    Spaces(usize),
    Tab,
}

pub fn detect_indent(text: &str) -> Indent {
    let body = text.trim();
    if !body.contains('\n') {
        return Indent::OneLine;
    }
    let b = body.as_bytes();
    if !matches!(b.first(), Some(b'{') | Some(b'[')) {
        return Indent::Spaces(2);
    }
    let skip_blanks = |mut i: usize| {
        while i < b.len() && (b[i] == b' ' || b[i] == b'\t') {
            i += 1;
        }
        i
    };
    let after_bracket = skip_blanks(1);
    let mut starts = vec![after_bracket];
    if body[after_bracket..].starts_with("/*") {
        let mut from = after_bracket + 2;
        while let Some(n) = body[from..].find("*/") {
            starts.push(from + n + 2);
            from += n + 1;
        }
        starts.remove(0);
        starts.push(after_bracket);
    }
    for s in starts {
        let mut i = skip_blanks(s);
        if b.get(i) == Some(&b'\r') {
            i += 1;
        }
        if b.get(i) != Some(&b'\n') {
            continue;
        }
        let ws_start = i + 1;
        let ws_end = skip_blanks(ws_start);
        if ws_end == ws_start {
            continue;
        }
        if body[ws_end..].chars().next().is_some_and(|c| !c.is_whitespace()) {
            let ws = &body[ws_start..ws_end];
            return if ws.contains('\t') { Indent::Tab } else { Indent::Spaces(ws.len()) };
        }
    }
    Indent::Spaces(2)
}

pub fn to_json_text(v: &Value, indent: &Indent) -> String {
    let bytes = match indent {
        Indent::OneLine => serde_json::to_vec(v).expect("JSON values always serialize"),
        Indent::Tab => pretty(v, b"\t"),
        Indent::Spaces(n) => pretty(v, " ".repeat(*n).as_bytes()),
    };
    String::from_utf8(bytes).expect("serde_json writes UTF-8")
}

fn pretty(v: &Value, indent: &[u8]) -> Vec<u8> {
    let mut buf = Vec::new();
    let mut ser = serde_json::Serializer::with_formatter(&mut buf, serde_json::ser::PrettyFormatter::with_indent(indent));
    v.serialize(&mut ser).expect("JSON values always serialize");
    buf
}

pub fn compact_preview(v: &Value, limit: usize) -> (String, bool) {
    struct Capped {
        buf: Vec<u8>,
        cap: usize,
    }
    impl Write for Capped {
        fn write(&mut self, data: &[u8]) -> io::Result<usize> {
            let room = self.cap.saturating_sub(self.buf.len());
            self.buf.extend_from_slice(&data[..data.len().min(room)]);
            if data.len() > room { Err(io::Error::other("full")) } else { Ok(data.len()) }
        }
        fn flush(&mut self) -> io::Result<()> {
            Ok(())
        }
    }
    let mut w = Capped { buf: Vec::new(), cap: (limit + 1) * 4 };
    let cut = serde_json::to_writer(&mut w, v).is_err();
    let text = String::from_utf8_lossy(&w.buf).into_owned();
    (text, cut)
}

pub fn py_float_repr(x: f64) -> String {
    if x == 0.0 {
        return if x.is_sign_negative() { "-0.0".into() } else { "0.0".into() };
    }
    let sci = format!("{x:e}");
    let (mant, exp) = sci.split_once('e').expect("{:e} always has an exponent");
    let exp: i32 = exp.parse().expect("exponent is a number");
    let neg = mant.starts_with('-');
    let digits: String = mant.chars().filter(char::is_ascii_digit).collect();
    let decpt = exp + 1;
    let body = if decpt <= -4 || decpt > 16 {
        let mut m = digits[..1].to_string();
        if digits.len() > 1 {
            m.push('.');
            m.push_str(&digits[1..]);
        }
        let e = decpt - 1;
        format!("{m}e{}{:02}", if e < 0 { '-' } else { '+' }, e.abs())
    } else if decpt <= 0 {
        format!("0.{}{digits}", "0".repeat((-decpt) as usize))
    } else if decpt as usize >= digits.len() {
        format!("{digits}{}.0", "0".repeat(decpt as usize - digits.len()))
    } else {
        format!("{}.{}", &digits[..decpt as usize], &digits[decpt as usize..])
    };
    if neg { format!("-{body}") } else { body }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn comments_and_trailing_commas() {
        let (v, c) = parse_jsonc("{\n // a\n \"u\": \"https://x\", /* b */ \"l\": [1, 2,],\n}").unwrap();
        assert!(c);
        assert_eq!(v["u"], "https://x");
        assert_eq!(v["l"].as_array().unwrap().len(), 2);
        let (_, c) = parse_jsonc("{\"a\": 1}").unwrap();
        assert!(!c);
        let (v, c) = parse_jsonc("{\"a\": [1,],}").unwrap();
        assert!(!c);
        assert_eq!(v["a"][0], 1);
    }

    #[test]
    fn indents() {
        assert_eq!(detect_indent("{\"a\": 1}"), Indent::OneLine);
        assert_eq!(detect_indent("{\n    \"a\": 1\n}"), Indent::Spaces(4));
        assert_eq!(detect_indent("{\n\t\"a\": 1\n}"), Indent::Tab);
        assert_eq!(detect_indent("{ /* x */\n  \"a\": 1\n}"), Indent::Spaces(2));
        assert_eq!(detect_indent("{\n\n  \"a\": 1\n}"), Indent::Spaces(2));
        assert_eq!(detect_indent("{\r\n   \"a\": 1\r\n}"), Indent::Spaces(3));
    }

    #[test]
    fn python_float_text() {
        for (x, want) in [(1.0, "1.0"), (0.1, "0.1"), (1e-5, "1e-05"), (1e20, "1e+20"), (1.5e20, "1.5e+20"),
                          (1e16, "1e+16"), (1e15, "1000000000000000.0"), (0.0001, "0.0001"), (-2.5, "-2.5"),
                          (123.456, "123.456"), (1.2345678901234568e17, "1.2345678901234568e+17"), (-0.0, "-0.0")] {
            assert_eq!(py_float_repr(x), want);
        }
    }

    #[test]
    fn writes_like_python() {
        let v: Value = serde_json::from_str(r#"{"a": [1, {"b": true}], "c": {}, "d": [], "e": "é\n"}"#).unwrap();
        assert_eq!(to_json_text(&v, &Indent::OneLine), r#"{"a":[1,{"b":true}],"c":{},"d":[],"e":"é\n"}"#);
        assert_eq!(to_json_text(&v, &Indent::Spaces(2)),
                   "{\n  \"a\": [\n    1,\n    {\n      \"b\": true\n    }\n  ],\n  \"c\": {},\n  \"d\": [],\n  \"e\": \"é\\n\"\n}");
    }
}
