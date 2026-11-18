use std::fs;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Duration;

use serde_json::Value;

use crate::updates::{base, from_ureq, get_json, HttpError};
use crate::versions::newer;

pub const REPO: &str = "hxpeerr/skyblock-config-manager";
const APP: &str = "SkyblockConfigManager";
const MAX_DOWNLOAD: u64 = 512 * 1024 * 1024;

#[derive(Clone, Debug, PartialEq)]
pub struct Asset {
    pub name: String,
    pub size: u64,
    pub url: String,
}

#[derive(Clone, Debug, PartialEq)]
pub struct Release {
    pub tag: String,
    pub name: String,
    pub notes: String,
    pub page: String,
    pub published: String,
    pub assets: Vec<Asset>,
}

impl Release {
    pub fn version(&self) -> &str {
        self.tag.strip_prefix('v').unwrap_or(&self.tag)
    }

    pub fn is_newer_than(&self, version: &str) -> bool {
        newer(&self.tag, version)
    }

    pub fn asset(&self, name: &str) -> Option<&Asset> {
        self.assets.iter().find(|a| a.name == name)
    }
}

#[derive(Default)]
pub struct Progress {
    pub done: AtomicU64,
    pub total: AtomicU64,
}

impl Progress {
    pub fn fraction(&self) -> f32 {
        let total = self.total.load(Ordering::Relaxed);
        if total == 0 { 0.0 } else { self.done.load(Ordering::Relaxed) as f32 / total as f32 }
    }
}

pub fn release_page() -> String {
    format!("https://github.com/{REPO}/releases/latest")
}

pub fn asset_name() -> &'static str {
    if cfg!(windows) {
        "SkyblockConfigManager.exe"
    } else if cfg!(target_os = "macos") {
        "SkyblockConfigManager-macOS.zip"
    } else {
        "SkyblockConfigManager-Linux.zip"
    }
}

pub fn parse_release(v: &Value) -> Result<Release, String> {
    let text = |k: &str| v.get(k).and_then(Value::as_str).unwrap_or("").to_string();
    let tag = text("tag_name");
    if tag.is_empty() {
        return Err("the release has no version tag".into());
    }
    let assets = v
        .get("assets")
        .and_then(Value::as_array)
        .map(|list| {
            list.iter()
                .filter_map(|a| {
                    Some(Asset {
                        name: a.get("name")?.as_str()?.to_string(),
                        size: a.get("size").and_then(Value::as_u64).unwrap_or(0),
                        url: a.get("browser_download_url")?.as_str()?.to_string(),
                    })
                })
                .collect()
        })
        .unwrap_or_default();
    Ok(Release {
        name: text("name"),
        notes: text("body").replace("\r\n", "\n"),
        page: if text("html_url").is_empty() { release_page() } else { text("html_url") },
        published: text("published_at").chars().take(10).collect(),
        tag,
        assets,
    })
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Block {
    Heading,
    Bullet,
    Text,
    Gap,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Span {
    Plain,
    Strong,
    Code,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NoteLine {
    pub block: Block,
    pub spans: Vec<(Span, String)>,
}

pub fn note_lines(notes: &str) -> Vec<NoteLine> {
    let mut out: Vec<NoteLine> = Vec::new();
    for raw in notes.split('\n') {
        let line = raw.trim();
        if line.starts_with("<!--") {
            continue;
        }
        let rule = line.len() >= 3 && ['-', '*', '_'].iter().any(|&r| line.chars().all(|c| c == r));
        if line.is_empty() || rule {
            if out.last().is_some_and(|l| l.block != Block::Gap) {
                out.push(NoteLine { block: Block::Gap, spans: Vec::new() });
            }
            continue;
        }
        let hashes = line.len() - line.trim_start_matches('#').len();
        let (block, text) = if (1..=6).contains(&hashes) && line[hashes..].starts_with(' ') {
            (Block::Heading, line[hashes..].trim())
        } else if let Some(rest) = ["- ", "* ", "+ "].iter().find_map(|p| line.strip_prefix(p)) {
            (Block::Bullet, rest.trim())
        } else {
            (Block::Text, line)
        };
        out.push(NoteLine { block, spans: inline_spans(text) });
    }
    while out.last().is_some_and(|l| l.block == Block::Gap) {
        out.pop();
    }
    out
}

fn push_span(out: &mut Vec<(Span, String)>, span: Span, text: &str) {
    if text.is_empty() {
        return;
    }
    match out.last_mut() {
        Some((last, joined)) if *last == span => joined.push_str(text),
        _ => out.push((span, text.to_string())),
    }
}

fn link(s: &str) -> Option<(&str, &str)> {
    if !s.starts_with('[') {
        return None;
    }
    let close = s.find("](")?;
    let end = close + 2 + s[close + 2..].find(')')?;
    Some((&s[1..close], &s[end + 1..]))
}

fn inline_spans(text: &str) -> Vec<(Span, String)> {
    let mut out = Vec::new();
    let mut strong = false;
    let mut rest = text;
    while !rest.is_empty() {
        let plain = if strong { Span::Strong } else { Span::Plain };
        if let Some(r) = rest.strip_prefix("**") {
            strong = !strong;
            rest = r;
            continue;
        }
        if let Some(r) = rest.strip_prefix('`') {
            if let Some(end) = r.find('`') {
                push_span(&mut out, Span::Code, &r[..end]);
                rest = &r[end + 1..];
                continue;
            }
        }
        if let Some((label, after)) = link(rest) {
            push_span(&mut out, plain, label);
            rest = after;
            continue;
        }
        let n = rest.char_indices().skip(1).find(|&(_, c)| matches!(c, '*' | '`' | '[')).map_or(rest.len(), |(i, _)| i);
        push_span(&mut out, plain, &rest[..n]);
        rest = &rest[n..];
    }
    out
}

pub fn latest_release() -> Result<Release, String> {
    let url = format!("{}/repos/{REPO}/releases/latest", base("SCM_RELEASES_API", "https://api.github.com"));
    match get_json(&url) {
        Ok(v) => parse_release(&v),
        Err(HttpError::Status(404)) => Err("there's no release yet".into()),
        Err(e) => Err(e.to_string()),
    }
}

pub fn download(asset: &Asset, dest: &Path, progress: &Progress) -> Result<(), String> {
    progress.total.store(asset.size, Ordering::Relaxed);
    progress.done.store(0, Ordering::Relaxed);
    let agent: ureq::Agent = ureq::Agent::config_builder()
        .timeout_global(Some(Duration::from_secs(900)))
        .user_agent(format!("skyblock-config-manager/{}", crate::VERSION))
        .build()
        .into();
    let mut resp = agent.get(&asset.url).call().map_err(|e| from_ureq(e).to_string())?;
    let mut reader = resp.body_mut().with_config().limit(MAX_DOWNLOAD).reader();
    let mut file = fs::File::create(dest).map_err(|e| e.to_string())?;
    let mut buf = vec![0u8; 1 << 16];
    let mut done = 0u64;
    loop {
        let n = reader.read(&mut buf).map_err(|e| e.to_string())?;
        if n == 0 {
            break;
        }
        file.write_all(&buf[..n]).map_err(|e| e.to_string())?;
        done += n as u64;
        progress.done.store(done, Ordering::Relaxed);
    }
    file.sync_all().map_err(|e| e.to_string())?;
    if asset.size > 0 && done != asset.size {
        let _ = fs::remove_file(dest);
        return Err(format!("the download stopped early ({done} of {} bytes)", asset.size));
    }
    Ok(())
}

pub fn bundle_of(exe: &Path) -> Option<PathBuf> {
    let macos = exe.parent()?;
    let contents = macos.parent()?;
    let bundle = contents.parent()?;
    let is_bundle = macos.file_name()? == "MacOS"
        && contents.file_name()? == "Contents"
        && bundle.extension().is_some_and(|e| e == "app");
    is_bundle.then(|| bundle.to_path_buf())
}

pub fn install(downloaded: &Path, exe: &Path) -> Result<PathBuf, String> {
    if cfg!(windows) {
        replace_exe(downloaded, exe)
    } else if let Some(bundle) = bundle_of(exe).filter(|_| cfg!(target_os = "macos")) {
        replace_bundle_contents(downloaded, &bundle)
    } else {
        replace_binary_from_zip(downloaded, exe)
    }
}

pub fn old_exe(exe: &Path) -> PathBuf {
    let mut name = exe.file_name().unwrap_or_default().to_os_string();
    name.push(".old");
    exe.with_file_name(name)
}

pub fn replace_exe(new: &Path, exe: &Path) -> Result<PathBuf, String> {
    let old = old_exe(exe);
    let _ = fs::remove_file(&old);
    fs::rename(exe, &old).map_err(|e| format!("couldn't move the running app aside: {e}"))?;
    if let Err(e) = fs::rename(new, exe).or_else(|_| fs::copy(new, exe).map(|_| ())) {
        let _ = fs::rename(&old, exe);
        return Err(format!("couldn't put the new version in place: {e}"));
    }
    let _ = fs::remove_file(new);
    Ok(exe.to_path_buf())
}

fn zip_entry_bytes(zip_path: &Path, wanted: impl Fn(&str) -> bool) -> Result<Vec<(String, Vec<u8>, Option<u32>)>, String> {
    let file = fs::File::open(zip_path).map_err(|e| e.to_string())?;
    let mut z = zip::ZipArchive::new(file).map_err(|e| format!("the download isn't a valid zip: {e}"))?;
    let mut out = Vec::new();
    for i in 0..z.len() {
        let mut entry = z.by_index(i).map_err(|e| e.to_string())?;
        let name = entry.name().map_err(|e| e.to_string())?.replace('\\', "/");
        if entry.is_dir() || !wanted(&name) || name.split('/').any(|p| p == "..") {
            continue;
        }
        let mut data = Vec::new();
        entry.read_to_end(&mut data).map_err(|e| e.to_string())?;
        out.push((name, data, entry.unix_mode()));
    }
    Ok(out)
}

#[cfg(unix)]
fn set_mode(path: &Path, mode: u32) {
    use std::os::unix::fs::PermissionsExt;
    let _ = fs::set_permissions(path, fs::Permissions::from_mode(mode & 0o7777));
}

#[cfg(not(unix))]
fn set_mode(_path: &Path, _mode: u32) {}

pub fn replace_binary_from_zip(zip_path: &Path, exe: &Path) -> Result<PathBuf, String> {
    let entries = zip_entry_bytes(zip_path, |n| n.rsplit('/').next() == Some(APP))?;
    let (_, data, mode) = entries.into_iter().next().ok_or("the download doesn't contain the app")?;
    let mut name = exe.file_name().unwrap_or_default().to_os_string();
    name.push(".new");
    let new = exe.with_file_name(name);
    fs::write(&new, &data).map_err(|e| e.to_string())?;
    set_mode(&new, mode.unwrap_or(0o755) | 0o755);
    fs::rename(&new, exe).map_err(|e| {
        let _ = fs::remove_file(&new);
        format!("couldn't put the new version in place: {e}")
    })?;
    let _ = fs::remove_file(zip_path);
    Ok(exe.to_path_buf())
}

pub fn replace_bundle_contents(zip_path: &Path, bundle: &Path) -> Result<PathBuf, String> {
    let entries = zip_entry_bytes(zip_path, |n| n.split('/').nth(1) == Some("Contents") && n.split('/').next().is_some_and(|b| b.ends_with(".app")))?;
    if !entries.iter().any(|(n, _, _)| n.ends_with(&format!("/Contents/MacOS/{APP}"))) {
        return Err("the download doesn't contain the app".into());
    }
    let contents = bundle.join("Contents");
    let staged = bundle.join("Contents.new");
    let old = bundle.join("Contents.old");
    let _ = fs::remove_dir_all(&staged);
    let _ = fs::remove_dir_all(&old);
    for (name, data, mode) in &entries {
        let rel: PathBuf = name.split('/').skip(2).collect();
        let path = staged.join(rel);
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }
        fs::write(&path, data).map_err(|e| e.to_string())?;
        if let Some(m) = mode {
            set_mode(&path, *m);
        }
    }
    fs::rename(&contents, &old).map_err(|e| format!("couldn't move the running app aside: {e}"))?;
    if let Err(e) = fs::rename(&staged, &contents) {
        let _ = fs::rename(&old, &contents);
        return Err(format!("couldn't put the new version in place: {e}"));
    }
    let _ = fs::remove_dir_all(&old);
    let _ = fs::remove_file(zip_path);
    Ok(bundle.to_path_buf())
}

pub fn download_path(exe: &Path) -> PathBuf {
    exe.with_file_name(format!("{}.download", asset_name()))
}

pub fn cleanup(exe: &Path) {
    let _ = fs::remove_file(download_path(exe));
    if let Some(bundle) = bundle_of(exe) {
        let _ = fs::remove_dir_all(bundle.join("Contents.old"));
        let _ = fs::remove_dir_all(bundle.join("Contents.new"));
    }
    let old = old_exe(exe);
    for _ in 0..40 {
        if !old.exists() || fs::remove_file(&old).is_ok() {
            return;
        }
        std::thread::sleep(Duration::from_millis(250));
    }
}

pub fn restart(target: &Path) -> std::io::Result<()> {
    if target.extension().is_some_and(|e| e == "app") {
        std::process::Command::new("open").arg("-n").arg(target).spawn()?;
    } else {
        let mut cmd = std::process::Command::new(target);
        if let Some(dir) = std::env::current_dir().ok() {
            cmd.current_dir(dir);
        }
        cmd.spawn()?;
    }
    Ok(())
}

pub fn open_in_browser(url: &str) {
    let result = if cfg!(windows) {
        std::process::Command::new("cmd").args(["/C", "start", "", url]).spawn()
    } else if cfg!(target_os = "macos") {
        std::process::Command::new("open").arg(url).spawn()
    } else {
        std::process::Command::new("xdg-open").arg(url).spawn()
    };
    let _ = result;
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn zip_with(path: &Path, files: &[(&str, &[u8], u32)]) {
        let mut z = zip::ZipWriter::new(fs::File::create(path).unwrap());
        for (name, data, mode) in files {
            let opts = zip::write::SimpleFileOptions::default().unix_permissions(*mode);
            z.start_file(*name, opts).unwrap();
            z.write_all(data).unwrap();
        }
        z.finish().unwrap();
    }

    #[test]
    fn reads_a_release() {
        let r = parse_release(&json!({"tag_name": "v4.1.0", "name": "v4.1.0", "body": "a\r\nb", "html_url": "https://x/r",
            "published_at": "2026-11-20T10:00:00Z", "assets": [{"name": "SkyblockConfigManager.exe", "size": 3,
            "browser_download_url": "https://x/a.exe"}, {"name": "broken"}]})).unwrap();
        assert_eq!(r.version(), "4.1.0");
        assert_eq!(r.notes, "a\nb");
        assert_eq!(r.published, "2026-11-20");
        assert_eq!(r.assets.len(), 1);
        assert!(r.is_newer_than("4.0.2"));
        assert!(!r.is_newer_than("4.1.0"));
        assert!(parse_release(&json!({"name": "x"})).is_err());
    }

    #[test]
    fn swaps_an_exe_and_keeps_the_old_one_aside() {
        let dir = tempfile::tempdir().unwrap();
        let exe = dir.path().join("SkyblockConfigManager.exe");
        let new = dir.path().join("download.tmp");
        fs::write(&exe, b"old").unwrap();
        fs::write(&new, b"new").unwrap();
        replace_exe(&new, &exe).unwrap();
        assert_eq!(fs::read(&exe).unwrap(), b"new");
        assert_eq!(fs::read(old_exe(&exe)).unwrap(), b"old");
        fs::write(download_path(&exe), b"partial").unwrap();
        cleanup(&exe);
        assert!(!old_exe(&exe).exists());
        assert!(!download_path(&exe).exists());
        assert_eq!(fs::read(&exe).unwrap(), b"new");
    }

    #[test]
    fn reads_release_notes() {
        let notes = "<!-- made by GitHub -->\n## What's Changed\r\n* **Bold** and `code` by [someone](https://x)\n\n\n---\nPlain ** text\n\n";
        let line = |block, spans: &[(Span, &str)]| NoteLine { block, spans: spans.iter().map(|&(s, t)| (s, t.to_string())).collect() };
        assert_eq!(note_lines(notes), vec![
            line(Block::Heading, &[(Span::Plain, "What's Changed")]),
            line(Block::Bullet, &[(Span::Strong, "Bold"), (Span::Plain, " and "), (Span::Code, "code"), (Span::Plain, " by someone")]),
            line(Block::Gap, &[]),
            line(Block::Text, &[(Span::Plain, "Plain "), (Span::Strong, " text")]),
        ]);
        assert!(note_lines("\n \n").is_empty());
    }

    #[test]
    fn replaces_a_binary_from_the_linux_zip() {
        let dir = tempfile::tempdir().unwrap();
        let exe = dir.path().join("SkyblockConfigManager");
        let zip_path = dir.path().join("download.zip");
        fs::write(&exe, b"old").unwrap();
        zip_with(&zip_path, &[("SkyblockConfigManager", b"new", 0o755)]);
        replace_binary_from_zip(&zip_path, &exe).unwrap();
        assert_eq!(fs::read(&exe).unwrap(), b"new");
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            assert_eq!(fs::metadata(&exe).unwrap().permissions().mode() & 0o111, 0o111);
        }
        let bad = dir.path().join("bad.zip");
        zip_with(&bad, &[("readme.txt", b"x", 0o644)]);
        assert!(replace_binary_from_zip(&bad, &exe).is_err());
        assert_eq!(fs::read(&exe).unwrap(), b"new");
    }

    #[test]
    fn swaps_the_contents_of_a_mac_app() {
        let dir = tempfile::tempdir().unwrap();
        let bundle = dir.path().join("SkyblockConfigManager.app");
        fs::create_dir_all(bundle.join("Contents/MacOS")).unwrap();
        fs::write(bundle.join("Contents/MacOS/SkyblockConfigManager"), b"old").unwrap();
        fs::write(bundle.join("Contents/Info.plist"), b"old plist").unwrap();
        let exe = bundle.join("Contents/MacOS/SkyblockConfigManager");
        assert_eq!(bundle_of(&exe), Some(bundle.clone()));
        let zip_path = dir.path().join("mac.zip");
        zip_with(&zip_path, &[("SkyblockConfigManager.app/Contents/Info.plist", b"new plist", 0o644),
                              ("SkyblockConfigManager.app/Contents/MacOS/SkyblockConfigManager", b"new", 0o755),
                              ("SkyblockConfigManager.app/Contents/Resources/icon.icns", b"icon", 0o644)]);
        replace_bundle_contents(&zip_path, &bundle).unwrap();
        assert_eq!(fs::read(&exe).unwrap(), b"new");
        assert_eq!(fs::read(bundle.join("Contents/Info.plist")).unwrap(), b"new plist");
        assert!(bundle.join("Contents/Resources/icon.icns").exists());
        assert!(!bundle.join("Contents.old").exists());
    }
}
