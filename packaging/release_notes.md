**SkyBlock Config Manager** finds settings that overlap between Fabric SkyBlock mods and keeps each feature switched on in only the mod you choose.

### Download
- **`SkyBlockConfigManager.exe`**: a single file for 64-bit Windows 10 or 11. Nothing to install, and no Python needed.
- **`SkyBlockConfigManager.zip`**: the same program, zipped, in case your browser blocks the .exe download.

Put it in your `.minecraft` folder (or your launcher's instance folder) and double-click it; it finds the `config` folder by itself. It keeps its own settings in `skyblock_config_manager.settings.json` next to the exe, and backs up each config as a `.bak_*` file before it's first saved.

The exe isn't code-signed, so the first time you run it Windows may show "Windows protected your PC". Click **More info**, then **Run anyway**.

SHA-256 of `SkyBlockConfigManager.exe`: `{sha256}`

Built from this tag on GitHub's Windows runners with Python {python} and PyInstaller {pyinstaller}. To build it yourself, run `packaging\build_exe.bat`.
