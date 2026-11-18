# SkyBlock Config Manager

Running several Hypixel Skyblock mods at once usually means duplicate features crowding your screen: two dungeon maps in the corner, three Diana burrow guessers drawing lines, and multiple pest alerts going off at the same time. SkyBlock Config Manager reads your mod config files, finds the features that more than one mod has, and keeps each one turned on in only the mod you choose.

* **83 shared features:** Covers 13 parts of the game, from Dungeons and Kuudra to Diana and the HUD.
* **You pick which mod does what:** Choose a main mod for each area, make exceptions for single features, or turn a feature off in every mod.
* **Preview every change:** Nothing changes on your computer until you look over the list of current and recommended settings.
* **Safe saving:** Original files are backed up before saving, and the app will never overwrite a file if the game changed it while the app was open.
* **Edit any setting:** Search, filter, and change any setting from the supported mods, not just the shared ones.
* **Update checker:** Shows which version of each mod you have installed and checks Modrinth and CurseForge for newer versions.
* **Setting names that adjust to your game version:** Uses the right setting names for whichever Minecraft version you pick, so shared features still populate even if a mod renamed them in an update.
* **Automatic support for new mods:** Finds your other installed Hypixel SkyBlock mods, their config files, and their settings on its own, even if they aren't supported yet, so you can browse and edit them.

## Download

* **Windows:** Download `SkyBlockConfigManager.exe` from the [latest release](../../releases/latest) for 64-bit Windows 10 or 11. Everything is in one file with nothing to install. The first time you open it, Windows might show a "Windows protected your PC" pop-up. Just click **More info**, then **Run anyway**.
* **macOS, Linux, or Windows with Python:** Download `skyblock_config_manager.py` from the [latest release](../../releases/latest) and run it with Python 3.8 or newer. It only uses built-in Python tools, so you don't need to install anything extra.
*Do note that only the exe and python files have been tested on windows 11. I will test it on linux at a later date; unable to test on macOS as my laptop is broken.

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
| [Skyblock Overhaul (SBO)](https://modrinth.com/mod/skyblock-overhaul) | `sbo/config.jsonc` | 8 |

Settings are based on each mod's Fabric version for Minecraft 26.1.2. Versions from 1.21.5 to 26.3 work too: just pick yours on the Overview tab, and the app uses the setting names each mod had in that version. A mod only shows up if its config file is found, and a feature is only compared when at least two of your mods have it.

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
2. **Open the app:** It looks for your `config` folder on its own by checking the folder you used last time, the folder the app is in, or your normal `.minecraft` folder. If it can't find it, click **Browse…** and pick it yourself.
3. **Check the Overview tab:** See which mods were found, how many settings overlap, and how many don't match your choices yet. Pick your **Minecraft version** and click **Check for updates** to see if Modrinth or CurseForge has newer versions for your game.
4. **Pick your Priorities:** For each area, choose a **Prioritized mod**. That mod's features will stay on, and duplicate features in your other mods will be turned off. To make an exception for a single feature, pick another mod (or **Off in every mod**) in its **Use** column.
5. **View or edit settings:** The **Shared** tab lists every overlapping setting and highlights any that don't match your choices. The **Unique** tab lists everything else. In both tabs, you can double-click a `true`/`false` setting to flip it, or double-click any other setting to type a new value.
6. **Apply your choices:** Click **Resolve conflicts** to apply all recommended changes at once, or **Apply area** to update just one section. Nothing is saved to your files yet.
7. **Save and play:** Press `Ctrl+S` or click **Save changes** to update your files, then start Minecraft.

If the main mod you picked for an area doesn't have a certain feature, the app keeps that feature on in the first mod on the list that does have it. The app remembers your choices for next time.

## Keeping Your Configs Safe

* **Automatic backups:** The first time a file is saved after you open the app, a backup copy of the original is saved right next to it as `<name>.bak_<date>_<time>`. To undo your changes, delete the updated file and remove `.bak_<date>_<time>` from the backup's name.
* **No overwriting while the game is open:** If a file was changed on your computer after you loaded it (usually because Minecraft was still running), the app won't save over it. Close the game, click **Reload**, and make your changes again.
* **Heads-up on file notes:** Extra notes written inside `.jsonc` files can't be kept when saving, so the app lets you know which files have them and asks before saving.

## Troubleshooting

* **A mod says "not found" on the Overview tab:** The app couldn't find its config file in the usual spot. Make sure you opened the right `config` folder, or add the file's location to `MODS` at the top of `skyblock_config_manager.py`.
* **Every mod says "not installed":** The app checks mod versions by looking at the `.jar` files in the `mods` folder right next to your `config` folder.
