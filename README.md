# SkyBlock Config Manager

Running several Hypixel Skyblock mods at once usually means duplicate features crowding your screen: two dungeon maps in the corner, three Diana burrow guessers drawing lines, and multiple pest alerts going off at the same time. SkyBlock Config Manager reads your mod config files, finds the features that more than one mod has, and keeps each one turned on in only the mod you choose.

* **83 shared features:** Covers 13 parts of the game, from Dungeons and Kuudra to Diana and the HUD.
* **You pick which mod does what:** Choose a main mod for each area, make exceptions for single features, or turn a feature off in every mod.
* **Preview every change:** Nothing is written to your files until you click **Save changes**, so you can look over every current and recommended value first.
* **Safe saving:** Original files are backed up before saving, and the app will never overwrite a file if the game changed it while the app was open.
* **Edit any setting:** Search, filter, and change any setting from your SkyBlock mods, not just the shared ones. Debug settings are locked so they can't be changed.
* **Update checker:** Shows which version of each mod you have installed and checks Modrinth and CurseForge for newer builds for your Minecraft version.
* **Setting names that adjust to your game version:** Uses the right setting names for whichever Minecraft version you pick, so shared features still populate even if a mod renamed them in an update.
* **Automatic support for new mods:** Finds your other installed Hypixel SkyBlock mods, their config files, and their settings on its own, even if they aren't supported yet, so you can browse and edit them.

## Download

* **Windows:** Download `SkyBlockConfigManager.exe` from the [latest release](../../releases/latest) for 64-bit Windows 10 or 11 (or `SkyBlockConfigManager.zip` if your browser blocks the .exe). Everything is in one file with nothing to install. The first time you open it, Windows might show a "Windows protected your PC" pop-up. Just click **More info**, then **Run anyway**.
* **macOS, Linux, or Windows with Python:** Download `skyblock_config_manager.py` from the [latest release](../../releases/latest) and run it with Python 3.8 or newer. It only uses built-in Python tools, so you don't need to install anything extra.

```bash
python3 skyblock_config_manager.py
```

On Windows, you can run `py skyblock_config_manager.py`. On Debian or Ubuntu Linux, you might need to install Tkinter first by running `sudo apt install python3-tk`.

*Do note that only the exe and Python files have been tested on Windows 11. I will test it on Linux at a later date; unable to test on macOS as my laptop is broken.*

## Supported Mods

The app looks for these Fabric mods inside your `.minecraft/config` folder:

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
| [Skyblock Overhaul (SBO)](https://modrinth.com/mod/skyblock-overhaul) | `sbo/config.jsonc` | 8 |

Settings are based on each mod's Fabric version for Minecraft 26.1.2. The **Minecraft version** menu on the Overview tab also has 1.21.5, 1.21.7, 1.21.8, 1.21.10, 1.21.11, 26.1, 26.1.1, 26.2, and 26.3: pick yours, and the app uses the setting names each mod had in that version. A mod is only used if its config file is found (a few older file names are checked too), and a feature is only compared when at least two of your mods have it.

Here are the 13 parts of the game and examples of the shared features they include:

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

Using a mod that isn't on the list? [Open an issue](../../issues/new) to ask for it to be added. Make sure to include:

* **Mod name and link:** A link to the mod's Modrinth, CurseForge, or GitHub page.

Until it's added, the app still finds other Hypixel SkyBlock mods on its own and shows their settings on the **Unique** tab, but it can't compare their features with your other mods.

## How to Use It

1. **Close Minecraft:** The game saves its settings when it closes, which would undo any changes you make here.
2. **Open the app:** It finds your `config` folder on its own (see [Finding Your Configs](#finding-your-configs)), so the easiest place for the .exe is your `.minecraft` folder or your launcher's instance folder. If it can't find the folder or picks the wrong one, click **Browse…**, or paste the folder's location into the **Config folder** box and press Enter.
3. **Check the Overview tab:** Each mod gets a row showing its config file, how many settings it has, how many of them are shared with other mods, how many don't match your choices yet (conflicts), and which version is installed. Mods the app found on its own are listed last, marked "(found)". Pick your **Minecraft version**, then click **Check for updates** to see if Modrinth or CurseForge has a newer build for your game. The **Activity** log underneath lists what the app has done, including any files it couldn't read.
4. **Pick your Priorities:** The list on the left shows how many conflicts each area has (✓ when there are none). For each area, choose a **Prioritized mod**. That mod's features will stay on, and duplicate features in your other mods will be turned off; the **Turns off** column shows which mods lose each feature. To make an exception for a single feature, pick another mod (or **Off in every mod**) in its **Use** column.
5. **View or edit settings:** The **Shared** tab lists every overlapping setting with its current and recommended value, and highlights any that don't match your choices. The **Unique** tab lists everything else. Both tabs have a search box, an area or mod filter, and a **Conflicts only** checkbox. Double-click a `true`/`false` setting (or select it and press Enter) to flip it, or double-click any other setting to type a new value; the app checks that it fits the setting, like a whole number or a JSON list. **Use recommended** fixes just the selected setting. Debug settings are shown in gray and can't be edited. Each tab shows up to 2,500 settings at a time, so search to narrow down big lists.
6. **Apply your choices:** Click **Resolve conflicts** to apply all recommended changes at once, or **Apply area** on the Priorities tab to update just one area. Nothing is saved to your files yet; the number of unsaved changes is shown in the bottom-right corner.
7. **Save and play:** Press `Ctrl+S` or click **Save changes** to update your files, then start Minecraft.

## How It Works

### Finding Your Configs

When it opens, the app uses the first of these folders that has a supported mod's config file in it:

1. The folder you used last time.
2. The folder you started the app from or the folder the .exe is in, or a `config`, `minecraft/config`, or `.minecraft/config` folder inside it. The .exe also checks the `config` folder next to the one it's in, for when it's in `.minecraft/mods`.
3. Your normal `.minecraft/config` folder: `%APPDATA%\.minecraft\config` on Windows, `~/Library/Application Support/minecraft/config` on macOS, or `~/.minecraft/config` on Linux.

Config files can be plain JSON or JSONC, which allows comments and trailing commas. Files over 25 MB are skipped. If a file can't be read, the Overview tab shows the mod as "unreadable" and the Activity log says why; your other mods still load. Every setting in a file gets its own row, named after where it sits in the file, like `Dungeon Map › Enable Map`.

### Comparing Features

The app has a built-in list of 83 features that more than one mod has, along with the name of each mod's on/off switch for it. A feature is only compared when at least two of your mods have its switch in their config files. Some mods use more than one switch for a feature, like SkyblockAddons' separate health and mana bars, and those switches always get the same recommended value.

For each compared feature, one mod keeps it on:

1. The mod you picked in the feature's **Use** column, if that mod has the feature. Picking **Off in every mod** means no mod keeps it.
2. Otherwise, the area's **Prioritized mod**, if it has the feature. Until you pick one (or if yours is gone), that's the first mod in the area's list.
3. Otherwise, the first mod in the feature's **Use** list.

That mod's switches are recommended to be `true`, and the same feature's switches in your other mods are recommended to be `false`. A switch that doesn't match its recommendation is a conflict: it's highlighted on the Shared tab and counted on the Overview and Priorities tabs. The app only recommends values for these `true`/`false` switches, and it doesn't change a setting until you edit it yourself or click **Use recommended**, **Apply area**, or **Resolve conflicts**.

A couple of special cases:

* **Firmament's inventory buttons** have no single on/off switch. Firmament still counts as having the feature, so if it keeps the feature, the inventory buttons in NoFrills and SkyOcean are turned off, but the app can't turn Firmament's off.
* **Three settings outside the shared features** also have a recommended value: Skyblocker's Quick Nav stays on, and Firmament's inventory button **Hover Text** stays on and **Only Inv** stays off. They're on the Unique tab, and **Resolve conflicts** sets them too.

### Setting Names for Each Minecraft Version

Mods sometimes rename a setting in an update. For every shared feature whose switch was renamed between 1.21.5 and 26.3, the app knows each name and which versions use it. It looks for the name used in the Minecraft version you picked first, then the other names, so shared features are still found even if your mod build is for a different version than the one you picked.

### Finding Other SkyBlock Mods

When it loads your `config` folder, the app also reads the mod files in the `mods` folder next to it. A mod that isn't on the supported list only counts as a Hypixel SkyBlock mod if its name or description mentions SkyBlock and either mentions Hypixel or uses Hypixel's Mod API, or if it's built on the SkyBlock API library. That keeps out mods for other Hypixel games and the unrelated sky-island survival mods that are also called "skyblock".

For each one it finds, the app loads the JSON and JSONC files in `config` that are named after the mod (like `modname.json` or `modname-config.json`), or every one of those files in a folder named after it. Cache files, backup files, and files over 2 MB are skipped. These mods show up on the Overview tab marked "(found)", and their settings are on the Unique tab, where you can search and edit them like any other setting. They aren't compared with your other mods, since the app doesn't know which of their settings match other mods' features.

### Locked Debug Settings

Debug and developer settings are shown in gray with the status "locked (debug)". You can't edit them, nothing is recommended for them, and **Resolve conflicts** never changes them. A setting is locked when it's in a debug or developer section, like SkyHanni's Dev category, Skyblocker's Debug category, or Firmament's developer settings, or when its own name only says it's a debug option, like the Debug option in NoFrills' Middle Click Override or SkyblockAddons' Developer Mode. This works the same way for mods the app finds on its own. Settings that are only about Minecraft's F3 debug screen, like SkyHanni's **Hide GUI in Debug Menu**, are normal features, so you can still edit them.

### Checking for Updates

* **Installed version:** The **Installed** column shows the version inside each mod's `.jar` file in the `mods` folder next to `config`.
* **Modrinth:** **Check for updates** looks for the newest Fabric build for the Minecraft version you picked. It asks Modrinth which project each installed file belongs to using the file's hash, so it doesn't matter what the file is called. If Modrinth doesn't recognize a supported mod's file, the app checks that mod's Modrinth page instead.
* **CurseForge:** Skyblocker and SkyOcean are also on CurseForge, so they're checked there too, and the newer of the two results is shown, marked "(CurseForge)". CurseForge is read through CFWidget, a public copy of CurseForge's project pages, because CurseForge's own API needs a private key.
* **Results:** The **Latest for** column (named after your Minecraft version, like **Latest for 26.1.2**) shows "up to date", the newer version (highlighted) when there's an update, "no *version* build" when a mod hasn't released one for your Minecraft version, or "not on Modrinth". Picking a different Minecraft version clears the results, since they were for the old version.
* **Going online:** The app only connects to the internet when you click **Check for updates**.

### Remembering Your Choices

The app remembers your config folder, Minecraft version, prioritized mods, and **Use** choices:

* **.exe:** They're kept in `skyblock_config_manager.settings.json` next to the .exe. If it can't save there (like in Program Files), it uses `.skyblock_config_manager.json` in your home folder instead.
* **Python:** They're kept in `.skyblock_config_manager.json` in your home folder.

If both files exist, the .exe uses whichever was saved last, so switching from the Python version to the .exe keeps your choices.

## Keeping Your Configs Safe

* **Automatic backups:** The first time a file is saved after you open the app (or click **Reload**), a backup copy of the original is saved right next to it as `<name>.bak_<date>_<time>`. Older backups are never overwritten. To undo your changes, delete the updated file and remove `.bak_<date>_<time>` from the backup's name.
* **No overwriting while the game is open:** If a file was changed on your computer after you loaded it (usually because Minecraft was still running), the app won't save over it. Close the game, click **Reload**, and make your changes again.
* **No half-saved files:** Each file is written to a temporary copy first and then swapped in, so a crash or power cut can't leave a config half-written.
* **Your formatting stays:** Only files with changes are saved, and they keep their own indentation and setting order.
* **Heads-up on file notes:** Extra notes (comments) written inside config files, usually `.jsonc` ones, can't be kept when saving, so the app lets you know which files have them and asks before saving.
* **No lost edits:** The app asks before **Reload** or closing the window would throw away unsaved changes.

## Troubleshooting

* **A mod says "not found" on the Overview tab:** The app couldn't find its config file in the usual spot. Make sure you opened the right `config` folder. With the Python version, you can also add the file's location to `MODS` at the top of `skyblock_config_manager.py`.
* **A mod says "unreadable":** Its config file isn't valid JSON or is bigger than 25 MB. The Activity log on the Overview tab shows the exact problem.
* **A setting is gray and can't be edited:** It's a debug or developer setting, which the app locks. See [Locked Debug Settings](#locked-debug-settings).
* **Every mod says "not installed":** The app checks mod versions by looking at the `.jar` files in the `mods` folder right next to your `config` folder.
* **A SkyBlock mod you have isn't found:** The app can only find mods whose config files are JSON or JSONC and named after the mod. [Request it](#requesting-a-mod) so it can be added properly.
* **The update check failed:** Make sure you're online and try again. The Activity log shows what went wrong.
* **Something else went wrong:** Unexpected errors pop up with a short message, and the full details are in the Activity log. Include them when you [open an issue](../../issues/new).
* **Your antivirus flags the .exe:** This is a false alarm that's common for Python apps packed into an .exe with PyInstaller, because some malware is packed with the same tool. Since 3.4.0, the .exe is built with its own copy of PyInstaller's loader, so Microsoft Defender and most other antivirus programs don't flag it, though a few less common ones still might. Older versions are flagged more often, so make sure you have the [latest release](../../releases/latest). The .exe is built by GitHub from the source code in this repository, and each release lists its SHA-256 so you can check that you have the same file. If you'd rather not use it, run `skyblock_config_manager.py` with Python instead.
