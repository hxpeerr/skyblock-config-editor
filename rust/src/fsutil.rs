use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;

use crate::features::ModSpec;

pub type Stamp = (u64, u128);

pub fn stamp(p: &Path) -> io::Result<Stamp> {
    let m = fs::metadata(p)?;
    let ns = m.modified()?.duration_since(UNIX_EPOCH).map(|d| d.as_nanos()).unwrap_or(0);
    Ok((m.len(), ns))
}

pub fn read_text(p: &Path) -> io::Result<String> {
    let bytes = fs::read(p)?;
    let bytes = bytes.strip_prefix(b"\xef\xbb\xbf").unwrap_or(&bytes);
    let text = String::from_utf8(bytes.to_vec())
        .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, format!("not UTF-8 text ({e})")))?;
    Ok(if text.contains('\r') { text.replace("\r\n", "\n").replace('\r', "\n") } else { text })
}

pub fn atomic_write(path: &Path, text: &str) -> io::Result<()> {
    let dir = path.parent().filter(|d| !d.as_os_str().is_empty()).unwrap_or(Path::new("."));
    let name = path.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
    let mut tmp = tempfile::Builder::new().prefix(&format!("{name}.")).suffix(".tmp").tempfile_in(dir)?;
    tmp.write_all(text.as_bytes())?;
    tmp.as_file().sync_all()?;
    if let Ok(m) = fs::metadata(path) {
        let _ = fs::set_permissions(tmp.path(), m.permissions());
    }
    tmp.persist(path).map_err(|e| e.error)?;
    Ok(())
}

pub fn copy_with_times(src: &Path, dst: &Path) -> io::Result<()> {
    fs::copy(src, dst)?;
    let m = fs::metadata(src)?;
    let times = fs::FileTimes::new().set_accessed(m.accessed()?).set_modified(m.modified()?);
    fs::OpenOptions::new().write(true).open(dst)?.set_times(times)
}

pub fn sorted_entries(dir: &Path) -> io::Result<Vec<PathBuf>> {
    let mut out: Vec<PathBuf> = fs::read_dir(dir)?.filter_map(|e| e.ok().map(|e| e.path())).collect();
    out.sort_by(|a, b| sort_key(a).cmp(&sort_key(b)));
    Ok(out)
}

fn sort_key(p: &Path) -> String {
    let s = p.to_string_lossy().into_owned();
    if cfg!(windows) { s.to_lowercase() } else { s }
}

pub fn has_json_suffix(p: &Path) -> bool {
    p.extension().map(|e| e.to_string_lossy().to_lowercase()).is_some_and(|e| e == "json" || e == "jsonc")
}

pub fn find_files(folder: &Path, spec: &ModSpec) -> Vec<PathBuf> {
    if let Some(d) = &spec.dir {
        let found: Vec<PathBuf> = sorted_entries(&folder.join(d))
            .unwrap_or_default()
            .into_iter()
            .filter(|p| has_json_suffix(p) && p.is_file())
            .collect();
        if !found.is_empty() {
            return found;
        }
    }
    for rel in &spec.files {
        let p = folder.join(rel);
        if p.is_file() {
            return vec![p];
        }
    }
    Vec::new()
}
