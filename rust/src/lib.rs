pub mod features;
pub mod fsutil;
pub mod jars;
pub mod jsonc;
pub mod prefs;
pub mod text;
pub mod updates;
pub mod value;
pub mod versions;
pub mod workspace;

pub const VERSION: &str = env!("CARGO_PKG_VERSION");
pub const APP_TITLE: &str = "SkyBlock Config Manager";
pub const OFF: &str = "Off";
pub const MAX_FILE_BYTES: u64 = 25 * 1024 * 1024;
pub const AUTO_MAX_BYTES: u64 = 2 * 1024 * 1024;
