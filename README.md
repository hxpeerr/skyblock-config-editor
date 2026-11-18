# Skyblock Config Manager

Running several Hypixel Skyblock mods at once usually crowds your screen with duplicates: two dungeon maps in the corner, three Diana burrow guessers drawing lines, and multiple pest alerts going off at the same time. Skyblock Config Manager reads your mod settings, finds the features that overlap, and keeps each one turned on in only the mod you choose.

* **83 shared features:** Covers 13 parts of the game, from Dungeons and Kuudra to Diana and the HUD.
* **You pick which mod does what:** Choose a main mod for each area, make exceptions for single features, or turn a feature off in every mod.
* **Safe saving:** Nothing changes until you click **Save changes**, and your original files are backed up first.
* **Edit any setting:** Search and change any setting from your SkyBlock mods, not just the shared ones. Debug settings are locked.
* **Update checker:** Checks Modrinth and CurseForge for newer versions of your mods.
* **Setting names that adjust to your game version:** Uses the right setting names for whichever Minecraft version you pick, so shared features still populate even if a mod renamed them in an update.
* **Automatic support for new mods:** Finds your other SkyBlock mods and their settings on its own, even if they aren't supported yet.

## Download

* **Windows:** Download `SkyBlockConfigManager.exe` from the [latest release](../../releases/latest), or the `.zip` if your browser blocks the .exe. If Windows shows "Windows protected your PC", click **More info**, then **Run anyway**.
* **macOS or Linux:** Download `skyblock_config_manager.py` from the [latest release](../../releases/latest) and run it with Python 3.8 or newer. On Debian or Ubuntu, install Tkinter first with `sudo apt install python3-tk`.

```bash
python3 skyblock_config_manager.py
```

*Do note that only the exe and Python files have been tested on Windows 11. I will test it on Linux at a later date; unable to test on macOS as my laptop is broken.*

## Supported Mods

| Mod | Config File |
|---|---|
| [NoFrills](https://modrinth.com/mod/nofrills) | `NoFrills/Configuration.json` |
| [SkyHanni](https://modrinth.com/mod/skyhanni) | `skyhanni/config.json` |
| [Skyblocker](https://modrinth.com/mod/skyblocker-liap) | `skyblocker.json` |
| [Aaron's Mod](https://modrinth.com/mod/aaron-mod) | `aaron-mod.json` |
| [SkyblockAddons](https://modrinth.com/mod/skyblockaddons-unofficial) | `skyblockaddons/configurations.json` |
| [SkyOcean](https://modrinth.com/mod/skyocean) | `skyocean/config.jsonc` |
| [Firmament](https://modrinth.com/mod/firmament) | `firmament/` |
| [Odin](https://modrinth.com/mod/odin) | `odin/odin-config.json` |
| [Skyblock Overhaul (SBO)](https://modrinth.com/mod/skyblock-overhaul) | `sbo/config.jsonc` |

These are the Fabric versions of each mod, for Minecraft 1.21.5 to 26.3. Config files are read from your `.minecraft/config` folder.

## Requesting a Mod

Using a mod that isn't on the list? [Open an issue](../../issues/new) with a link to its Modrinth, CurseForge, or GitHub page.

## How to Use It

1. **Close Minecraft:** The game saves its settings when it closes, which would undo your changes.
2. **Open the app:** It finds your `config` folder on its own. If it doesn't, click **Browse…** and pick it.
3. **Overview tab:** Pick your **Minecraft version**. Click **Check for updates** to see newer versions of your mods.
4. **Priorities tab:** For each area, pick a **Prioritized mod**. Its features stay on, and the same features in your other mods are turned off. To change a single feature, pick another mod (or **Off in every mod**) in its **Use** column.
5. **Shared and Unique tabs:** Look over your settings. Double-click one to change it.
6. **Save:** Click **Resolve conflicts** to apply your choices, then **Save changes** (or press `Ctrl+S`).

## Backups

The first time a file is saved, the original is copied next to it as `<name>.bak_<date>_<time>`. To undo your changes, delete the updated file and remove `.bak_<date>_<time>` from the backup's name.

## Troubleshooting

* **A mod says "not found":** Make sure you opened the right `config` folder.
* **Every mod says "not installed":** The app reads mod versions from the `mods` folder next to your `config` folder.
* **A file wasn't saved:** Minecraft was probably still open. Close it, click **Reload**, and make your changes again.
* **Your antivirus flags the .exe:** This is a false alarm that's common for Python apps packaged with PyInstaller. Since 3.4.0, Microsoft Defender and most antivirus programs don't flag it. You can also use the `.py` file instead.
* **Something else went wrong:** The **Activity** log on the Overview tab has the details. Include them when you [open an issue](../../issues/new).
