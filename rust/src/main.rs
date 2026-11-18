// A window app: no console window behind it in release builds.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod app;

fn main() -> eframe::Result {
    app::run()
}
