//! SkyblockConfigManager: finds settings that overlap between Fabric Hypixel SkyBlock mods, lets
//! you choose which mod owns each feature area (and each feature), and rewrites the configs so only
//! the owner keeps it enabled.
//!
//! This library holds everything except the window, so the tests can drive it directly.

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
/// The app's name, as shown in the window title.
pub const APP_TITLE: &str = "SkyBlock Config Manager";
/// A feature override meaning "turn it off in every mod".
pub const OFF: &str = "Off";
/// Config files bigger than this aren't loaded.
pub const MAX_FILE_BYTES: u64 = 25 * 1024 * 1024;
/// Larger JSON in a found mod's folder is usually data, not settings.
pub const AUTO_MAX_BYTES: u64 = 2 * 1024 * 1024;
