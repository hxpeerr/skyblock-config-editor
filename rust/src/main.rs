#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod app;

fn main() -> eframe::Result {
    if std::env::args().nth(1).as_deref() == Some("--version") {
        println!("{}", scm::VERSION);
        return Ok(());
    }
    app::run()
}
