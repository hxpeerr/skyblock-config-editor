# SkyBlock Config Manager

Running several Fabric SkyBlock mods at once usually means duplicate features crowding your screen—two dungeon maps in the corner, three Diana burrow guessers drawing lines, and multiple pest alerts going off at the same time. SkyBlock Config Manager reads your mod config files, finds the features that more than one mod has, and keeps each one turned on in only the mod you choose.

![The Priorities tab: pick which mod handles each area, and override single features]

* **83 shared features:** Covers 13 parts of the game, from Dungeons and Kuudra to Diana and the HUD.
* **You pick which mod does what:** Choose a main mod for each area, make exceptions for single features, or turn a feature off in every mod.
* **Preview every change:** Nothing changes on your computer until you review the list of current and recommended settings.
* **Safe saving:** Original files are backed up before saving, and the app will never overwrite a file if the game changed it while the app was open.
* **Edit any setting:** Search, filter, and change any setting from the supported mods, not just the shared ones.
* **Update checker:** Shows which version of each mod you have installed and checks Modrinth for newer versions.
* **Nothing to install:** Runs as a single `.exe` file on Windows, or one Python file on any computer.

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
| [SkyblockAddons](https://modrinth.com/mod/skyblockaddons-unofficial) | `skyblockaddons/configurations.json` | Settings only |
| [SkyOcean](https://modrinth.com/mod/skyocean) | `skyocean/config.jsonc` | 15 |
| [Firmament](https://modrinth.com/mod/firmament) | `firmament/` (one file per feature) | 4 |
| [Odin](https://modrinth.com/mod/odin) | `odin/odin-config.json` | 29 |
| [Skyblock Overhaul (SBO)](https://modrinth.com/mod/skyblock-overhaul) | `SBO/config.jsonc` | 8 |

Settings are based on each mod's Fabric version for Minecraft 26.1.2. A mod only shows up if its config file is found, and a feature is only compared when at least two of your mods have it. You can browse and edit SkyblockAddons settings, though shared features aren't set up for it yet.

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

## How to Use It

1. **Close Minecraft:** The game saves its settings when it closes, which would undo any changes you make here.
2. **Open the app:** It looks for your `config` folder on its own—checking the folder you used last time, the folder the app is in, or your normal `.minecraft` folder. If it can't find it, click **Browse…** and pick it yourself.
3. **Check the Overview tab:** See which mods were found, how many settings overlap, and how many don't match your choices yet. Click **Check for updates** to compare your installed mods with the newest versions on Modrinth.
4. **Pick your Priorities:** For each area, choose a **Prioritized mod**. That mod's features will stay on, and duplicate features in your other mods will be turned off. To make an exception for a single feature, pick another mod (or **Off in every mod**) in its **Use** column.
5. **View or edit settings:** The **Shared** tab lists every overlapping setting and highlights conflicts. The **Unique** tab lists everything else. In both tabs, you can double-click a `true`/`false` setting to flip it, or double-click any other setting to type a new value.
6. **Apply your choices:** Click **Resolve conflicts** to apply all recommended changes at once, or **Apply area** to update just one section. Nothing is saved to your files yet.
7. **Save and play:** Press `Ctrl+S` or click **Save changes** to update your files, then start Minecraft.

If the main mod you picked for an area doesn't have a certain feature, the app keeps that feature on in the first mod on the list that does have it. The app remembers your choices for next time.

## Keeping Your Configs Safe

* **Automatic backups:** The first time a file is saved after you open the app, a backup copy of the original is saved right next to it as `<name>.bak_<date>_<time>`. To undo your changes, delete the updated file and remove `.bak_<date>_<time>` from the backup's name.
* **No overwriting while the game is open:** If a file was changed on your computer after you loaded it (usually because Minecraft was still running), the app won't save over it. Close the game, click **Reload**, and make your changes again.
* **Note awareness:** Notes written inside `.jsonc` files can't be kept when saving, so the app warns you which files have them and asks before saving.
* **Safe file writing:** Changes are written to a temporary file first so a computer crash won't leave you with a broken, half-saved file. The original spacing and line layout of each file are kept intact.
* **Unsaved change warnings:** If you try to reload or close the app before saving your changes, it will ask you first.

## Where the App Saves Your Choices

The app remembers your `config` folder and the mods you picked for each area:

* **Windows `.exe`:** Saves them in `skyblock_config_manager.settings.json` in the same folder as the `.exe`, so you can move the app around without losing your setup. If that folder is locked (like inside `Program Files`), it saves them in your Windows user folder instead.
* **Python script:** Saves them in `~/.skyblock_config_manager.json` in your home folder.

## Changing What the App Compares

Everything the app looks for is listed at the top of `skyblock_config_manager.py`:

* **`MODS`:** Lists where each mod keeps its config files, its mod ID (used to find its `.jar` file), and its Modrinth page name (used by **Check for updates**).
* **`AREAS`:** The list of categories shown in the Priorities tab, in order.
* **`FEATURES`:** Lists every shared feature and the setting name each mod uses to turn it on or off:

  ```python
  ("Events", "Diana burrow guess", {
      "SBO": "*spadeGuess",
      "SkyHanni": "event.diana.guess",
      "Skyblocker": "helpers.mythologicalRitual.enableMythologicalRitualHelper",
      "Firmament": "diana.ancestral-spade",
      "NoFrills": "dianaSolver.enabled"}),
  ```

  A setting name uses dots to show where it sits inside the file. A list of names means several settings turn on and off together. Putting a `*` at the start matches the end of a setting name, which helps when a mod moves its settings around in an update (`*spadeGuess` matches both `spadeGuess` and `burrows.spadeGuess`). Using `None` means the mod has the feature but no single on/off switch for it. The order of mods matters: the first mod listed is the fallback choice for that feature.
* **`PREFERRED`:** Settings you want to keep at a specific value even though no other mod shares them.
* **`LABELS`:** Clearer names for settings whose original names in the file are hard to read.

`GAME_VERSION` and `LOADER` tell **Check for updates** which Minecraft version and mod loader to look for. If you use the `.exe`, you will need to rebuild it after editing the Python file for your changes to show up.

## Building the `.exe` Yourself

On Windows, double-click `packaging\build_exe.bat`. It installs PyInstaller and creates `dist\SkyBlockConfigManager.exe` using `packaging\SkyBlockConfigManager.spec`. You need Python 3.8 or newer to build the `.exe`, but once it's built, the `.exe` runs on its own without Python.

## Troubleshooting

* **A mod says "not found" on the Overview tab:** Its config file isn't where the app expects it. Make sure you opened the right `config` folder, or add the file's location to `MODS` in the script.
* **Every mod says "not installed":** The app checks mod versions by looking at the `.jar` files in the `mods` folder right next to your `config` folder.
* **"It was changed on disk after loading":** Minecraft (or another program) changed the file while you had the app open. Close Minecraft, click **Reload**, and make your changes again.
* **`No module named 'tkinter'` (Linux):** Install Tkinter for your Linux version—for example, `sudo apt install python3-tk` on Debian or Ubuntu.
