# skyblock-config-editor

**SkyBlock Config Manager** finds settings that overlap between Fabric SkyBlock mods (NoFrills, SkyHanni, Skyblocker, Aaron's Mod, SkyBlockAddons, SkyOcean, Firmament, Odin, SBO), lets you choose which mod owns each feature area or single feature, and rewrites the configs so only that mod keeps it switched on. Each config is backed up as a `.bak_*` file before it is first saved.

## Download

Get `SkyBlockConfigManager.exe` from the [latest release](../../releases/latest). It's a single file for 64-bit Windows that runs without Python.

## Run it from source

With Python 3.8+ (standard library only):

```
python skyblock_config_manager.py
```

It finds your Minecraft `config` folder automatically, or you can browse to it.

## Build the portable Windows .exe

Double-click `packaging\build_exe.bat` (building needs Python once). The result, `dist\SkyBlockConfigManager.exe`, is a single file that runs without Python. It keeps its own settings in `skyblock_config_manager.settings.json` next to itself, or in your home folder if it can't write there.

## Adapting it to your pack

The tables at the top of `skyblock_config_manager.py` (`MODS`, `AREAS`, `FEATURES`, `PREFERRED`, `LABELS`) decide which mods and settings are compared. Rebuild the .exe after editing them.

## Publishing a release

GitHub Actions builds release copies on Windows (`.github/workflows/release.yml`):

1. Set `__version__` in `skyblock_config_manager.py` (for example `3.2.0`) and merge the change into `main`.
2. On GitHub, open **Releases → Draft a new release**, create the tag `v3.2.0` on `main` and publish it. Pushing the tag with git works too.

Within a few minutes the workflow builds the exe, checks that it starts and loads a config folder, and attaches the `.exe` and `.zip` to the release. If you left the release description empty, it fills that in as well. Pull requests that change the app get the same build and check.
