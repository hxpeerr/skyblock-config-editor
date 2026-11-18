# SkyBlock Config Manager

Running several Fabric SkyBlock mods at once usually means duplicate features crowding your screen—two dungeon maps in the corner, three Diana burrow guessers drawing lines, and multiple pest alerts going off at the same time. SkyBlock Config Manager reads your mod config files, finds the features that more than one mod has, and keeps each one turned on in only the mod you choose.

![The Priorities tab: pick which mod handles each area, and override single features](docs/priorities.png)

* **83 shared features:** Covers 13 parts of the game, from Dungeons and Kuudra to Diana and the HUD.
* **You pick which mod does what:** Choose a main mod for each area, make exceptions for single features, or turn a feature off in every mod.
* **Preview every change:** Nothing changes on your computer until you review the list of current and recommended settings.
* **Safe saving:** Original files are backed up before saving, and the app will never overwrite a file if the game changed it while the app was open.
* **Edit any setting:** Search, filter, and change any setting from the supported mods, not just the shared ones.
* **Update checker:** Shows which version of each mod you have installed and checks Modrinth for newer versions.

## Download

* **Windows:** Download `SkyBlockConfigManager.exe` from the [latest release](../../releases/latest) for 64-bit Windows 10 or 11. Everything is in one file with nothing to install. The first time you open it, Windows may show a "Windows protected your PC" pop-up—click **More info**, then **Run anyway**.
* **macOS, Linux, or Windows with Python:** Download `skyblock_config_manager.py` and run it with Python 3.8 or newer. It uses built-in Python tools, so you don't need to install any extra packages.

```bash
python3 skyblock_config_manager.py
```

On Windows, you can run `py skyblock_config_manager.py`. On Debian or Ubuntu Linux, you might need to install Tkinter first by running `sudo apt install python3-tk`.

## Supported Mods

The app looks for these mods inside your `.minecraft/config` folder:

| Mod | Config File | Shared Features |
|---|---|---:|
| [NoFrills](https://modrinth.com/mod/nofrills) | `NoFrills/Configuration.json` | 48 |
| [SkyHanni](https://modrinth.com/mod/skyhanni) | `skyhanni/config.json` | 41 |
| [Skyblocker](https://modrinth.com/mod/skyblocker-liap) | `skyblocker.json` | 49 |
| [Aaron's Mod](https://modrinth.com/mod/aaron-mod) | `aaron-mod.json` | 5 |
| [SkyblockAddons](https://modrinth.com/mod/skyblockaddons-unofficial) | `skyblockaddons/configurations.json` | 7 |
| [SkyOcean](https://modrinth.com/mod/skyocean) | `skyocean/config.jsonc` | 15 |
| [Firmament](https://modrinth.com/mod/firmament) | `firmament/` (one file per feature) | 4 |
| [Odin](https://modrinth.com/mod/odin) | `odin/odin-config.json` | 29 |
| [Skyblock Overhaul (SBO)](https://modrinth.com/mod/skyblock-overhaul) | `SBO/config.jsonc` | 8 |

Settings are based on each mod's Fabric version for Minecraft 26.1.2. Other versions from 1.21.5 to 26.3 work too: pick yours on the Overview tab. If a mod named a setting differently in your version, that feature just isn't compared for it. A mod only shows up if its config file is found, and a feature is only compared when at least two of your mods have it.

Here are the 13 areas of the game and examples of the shared features they include:

| Area | Features | Examples |
|---|---:|---|
| Dungeons | 15 | Dungeon map, terminal solvers, puzzle solvers, starred mob highlight, … |
| Kuudra | 7 | Supply waypoints, pearl waypoints, ballista build helper, Kuudra highlight, … |
| Slayers | 9 | Boss spawn alert, miniboss spawn alert, boss highlight, miniboss highlight, … |
| Farming | 3 | Pest finder, visitor helper, glowing mushrooms |
| Mining | 9 | Metal detector solver, fossil solver, corpse finder, corpse profit tracker, … |
| Foraging | 2 | Moonglade beacon solver, mute phantoms |
| Hunting | 3 | Shard tracker, lasso alert, invisibug highlight |
| Fishing | 4 | Bobber timer, hide other players' bobbers, lava replacement, fishing hook display |
| Events | 10 | Diana burrow guess, Diana arrow guess, nearby burrow detection, nearest warp hint, … |
| Rift | 1 | Enigma soul waypoints |
| GUI/HUD | 6 | Custom tab list, TPS display, health / mana bars, item ability cooldowns, … |
| Inventory | 6 | Inventory buttons, keep cursor position, anvil helper, experiment solvers, … |
| Misc | 8 | Etherwarp overlay, auto sprint, wardrobe keybinds, loadout keybinds, … |

## Requesting a Mod

Using a Fabric SkyBlock mod that isn't listed above? [Open an issue](../../issues/new) to ask for it to be added. To help get it supported quickly, include:

* **Mod name and link:** The mod's Modrinth, CurseForge, or GitHub page.
* **Config file:** Where the mod saves its settings inside your `config` folder, like `examplemod/config.json`.
* **Shared features:** Any features it has in common with the supported mods, like a dungeon map or a Diana burrow guesser, if you know them.

You can also add a mod yourself: the lists at the top of `skyblock_config_manager.py` explain how. Then run your edited `.py` file, or build your own `.exe` by double-clicking `packaging\build_exe.bat` (this needs Python 3.8 or newer).

## How to Use It

1. **Close Minecraft:** The game saves its settings when it closes, which would undo any changes you make here.
2. **Open the app:** It looks for your `config` folder on its own—checking the folder you used last time, the folder the app is in, or your normal `.minecraft` folder. If it can't find it, click **Browse…** and pick it yourself.
3. **Check the Overview tab:** See which mods were found, how many settings overlap, and how many don't match your choices yet. Pick your **Minecraft version**, then click **Check for updates** to compare your installed mods with the newest versions for it on Modrinth.
4. **Pick your Priorities:** For each area, choose a **Prioritized mod**. That mod's features will stay on, and duplicate features in your other mods will be turned off. To make an exception for a single feature, pick another mod (or **Off in every mod**) in its **Use** column.
5. **View or edit settings:** The **Shared** tab lists every overlapping setting and highlights conflicts. The **Unique** tab lists everything else. In both tabs, you can double-click a `true`/`false` setting to flip it, or double-click any other setting to type a new value.
6. **Apply your choices:** Click **Resolve conflicts** to apply all recommended changes at once, or **Apply area** to update just one section. Nothing is saved to your files yet.
7. **Save and play:** Press `Ctrl+S` or click **Save changes** to update your files, then start Minecraft.

If the main mod you picked for an area doesn't have a certain feature, the app keeps that feature on in the first mod on the list that does have it. The app remembers your choices for next time.

## Keeping Your Configs Safe

* **Automatic backups:** The first time a file is saved after you open the app, a backup copy of the original is saved right next to it as `<name>.bak_<date>_<time>`. To undo your changes, delete the updated file and remove `.bak_<date>_<time>` from the backup's name.
* **No overwriting while the game is open:** If a file was changed on your computer after you loaded it (usually because Minecraft was still running), the app won't save over it. Close the game, click **Reload**, and make your changes again.
* **Note awareness:** Notes written inside `.jsonc` files can't be kept when saving, so the app warns you which files have them and asks before saving.

## Troubleshooting

* **A mod says "not found" on the Overview tab:** Its config file isn't where the app expects it. Make sure you opened the right `config` folder, or add the file's location to `MODS` in the script.
* **Every mod says "not installed":** The app checks mod versions by looking at the `.jar` files in the `mods` folder right next to your `config` folder.
