fn main() {
    println!("cargo:rerun-if-changed=../features.jsonc");
    println!("cargo:rerun-if-changed=../packaging/icon.ico");
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("windows") {
        let mut res = winresource::WindowsResource::new();
        res.set_icon("../packaging/icon.ico");
        res.set("FileDescription", "SkyBlock Config Manager");
        res.set("ProductName", "SkyBlock Config Manager");
        res.set("OriginalFilename", "SkyblockConfigManager.exe");
        res.set("InternalName", "SkyblockConfigManager");
        res.compile().expect("couldn't add the Windows resources");
    }
}
