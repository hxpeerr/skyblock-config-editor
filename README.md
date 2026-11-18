# Skyblock Config Manager

Running several Hypixel Skyblock mods at once usually crowds your screen with duplicates: two dungeon maps in the corner, three Diana burrow guessers drawing lines, and multiple pest alerts going off at the same time. Skyblock Config Manager reads your mod settings, finds the features that overlap, and keeps each one turned on in only the mod you choose.

* **83 shared features:** Covers 13 parts of the game, from Dungeons and Kuudra to Diana and your heads-up display (HUD).
* **You pick which mod does what:** Choose a main mod for each part of the game, make exceptions for single features, or turn a feature off everywhere.
* **Safe saving:** Nothing changes until you click **Save changes**, and your original files are backed up automatically first.
* **Edit any setting:** Search and change any setting from your SkyBlock mods, not just the overlapping ones. Developer test settings are locked so nothing breaks by accident.
* **Update checker:** Checks Modrinth and CurseForge for newer versions of your mods.
* **Adapts to your game version:** Uses the right setting names for whichever Minecraft version you pick, so shared features still show up even if an update renamed them.
* **Finds new mods on its own:** Spots your other Hypixel SkyBlock mods and loads their settings automatically, even if they aren't officially supported yet.

## Download

* **Windows:** Download `SkyBlockConfigManager.exe` from the [latest release](../../releases/latest) (or the `.zip` file if your browser blocks the `.exe`). If a "Windows protected your PC" pop-up appears, click **More info**, then **Run anyway**.
* **macOS or Linux:** Download `skyblock_config_manager.py` from the [latest release](../../releases/latest) and run it with Python 3.8 or newer. On Debian or Ubuntu Linux, you may need to install Python's window tool first by running `sudo apt install python3-tk`.

```bash
python3 skyblock_config_manager.py
```

*Note: Both downloads have only been tested on Windows 11 so far. I will test on Linux later, and I can't test on macOS right now because my laptop is broken.*

## Supported Mods

| Mod | Settings File |
|---|---|
| [NoFrills](https://modrinth.com/mod/nofrills) | `NoFrills/Configuration.json` |
| [SkyHanni](https://modrinth.com/mod/skyhanni) | `skyhanni/config.json` |
| [Skyblocker](https://modrinth.com/mod/skyblocker-liap) | `skyblocker.json` |
| [Aaron's Mod](https://modrinth.com/mod/aaron-mod) | `aaron-mod.json` |
| [SkyblockAddons](https://modrinth.com/mod/skyblockaddons-unofficial) | `skyblockaddons/configurations.json` |
| [SkyOcean](https://modrinth.com/mod/skyocean) | `skyocean/config.jsonc` |
| [Firmament](https://modrinth.com/mod/firmament) | `firmament/` |
| [Odin](https://modrinth.com/mod/odin) | `odin/odin-config.json` |
| [SBO](https://modrinth.com/mod/skyblock-overhaul) | `sbo/config.jsonc` |

These are the Fabric versions of each mod for Minecraft 1.21.5 through 26.3. The app reads their settings from your `.minecraft/config` folder.

## Requesting a Mod

Using a mod that isn't on the list yet? [Open an issue](../../issues/new) with a link to its Modrinth, CurseForge, or GitHub page so it can be added.

## How to Use It

1. **Close Minecraft:** The game saves its own settings when you quit, which would undo any changes you make here.
2. **Open the app:** It finds your `config` folder on its own. If it can't find it, click **Browse…** and pick the folder yourself.
3. **Overview tab:** Pick your **Minecraft version** and click **Check for updates** to see if any of your mods have newer releases.
4. **Priorities tab:** Pick a **Prioritized mod** for each part of the game. That mod's features will stay on, and duplicate features in your other mods will turn off. To make an exception for a single feature, pick another mod (or **Off in every mod**) in its **Use** column.
5. **Shared and Unique tabs:** Browse through your settings, or double-click any setting to change it.
6. **Save:** Click **Resolve conflicts** to apply your choices, then click **Save changes** (or press `Ctrl+S`).

## Backups

The first time you save a file, the app makes a backup copy of the original right next to it named `<name>.bak_<date>_<time>`. If you ever want to undo your changes, delete the updated file and remove `.bak_<date>_<time>` from the backup's name.

## Troubleshooting

* **A mod says "not found":** Make sure you opened the right `config` folder.
* **Every mod says "not installed":** Make sure your `mods` folder is sitting right next to your `config` folder so the app can check which versions you have.
* **A file wasn't saved:** Minecraft was probably still running in the background. Close the game, click **Reload**, and apply your changes again.
* **Your antivirus flags the .exe:** This is a common false alarm for Python apps bundled into a single `.exe` file. Starting with version 3.4.0, Microsoft Defender and most other antivirus programs no longer flag it, or you can run the `.py` file instead.
* **Something else went wrong:** Check the **Activity** log on the Overview tab for the full details, and include them when you [open an issue](../../issues/new).
