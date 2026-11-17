# skyblock-config-editor

**SkyBlock Config Manager** finds settings that overlap between Fabric SkyBlock mods (NoFrills, SkyHanni, Skyblocker, Aaron's Mod, SkyBlockAddons, SkyOcean, Firmament, Odin, SBO), lets you choose which mod owns each feature area or single feature, and rewrites the configs so only that mod keeps it switched on. Each config is backed up as a `.bak_*` file before it is first saved.

## Run it

With Python 3.8+ (standard library only):

```
python skyblock_config_manager.py
```

It finds your Minecraft `config` folder automatically, or you can browse to it.

## Build the portable Windows .exe

Double-click `packaging\build_exe.bat` (building needs Python once). The result, `dist\SkyBlockConfigManager.exe`, is a single file that runs without Python. It keeps its own settings in `skyblock_config_manager.settings.json` next to itself, or in your home folder if it can't write there.

## Adapting it to your pack

The tables at the top of `skyblock_config_manager.py` (`MODS`, `AREAS`, `FEATURES`, `PREFERRED`, `LABELS`) decide which mods and settings are compared. Rebuild the .exe after editing them.
