# PyInstaller recipe for the portable Windows build: one .exe, no Python needed to run it.
#
#     pyinstaller --noconfirm --clean packaging/SkyblockConfigManager.spec
#
# (or double-click packaging/build_exe.bat). Output: dist/SkyblockConfigManager.exe
import os
import re

from PyInstaller.utils.win32.versioninfo import (FixedFileInfo, StringFileInfo, StringStruct,
                                                  StringTable, VarFileInfo, VarStruct, VSVersionInfo)

HERE = SPECPATH
SCRIPT = os.path.join(os.path.dirname(HERE), "skyblock_config_manager.py")
ICON = os.path.join(HERE, "icon.ico")
NAME = "SkyblockConfigManager"

with open(SCRIPT, encoding="utf-8") as f:
    VERSION = re.search(r'^__version__ = "(\d+(?:\.\d+){0,3})"', f.read(), re.M).group(1)
NUMS = tuple(int(x) for x in VERSION.split("."))
NUMS += (0,) * (4 - len(NUMS))

# File properties shown by Windows (right-click > Properties > Details).
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=NUMS, prodvers=NUMS, mask=0x3F, flags=0x0, OS=0x40004,
                      fileType=0x1, subtype=0x0, date=(0, 0)),
    kids=[
        StringFileInfo([StringTable("040904B0", [
            StringStruct("FileDescription", "SkyBlock Config Manager"),
            StringStruct("FileVersion", VERSION),
            StringStruct("InternalName", NAME),
            StringStruct("OriginalFilename", NAME + ".exe"),
            StringStruct("ProductName", "SkyBlock Config Manager"),
            StringStruct("ProductVersion", VERSION),
        ])]),
        VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
    ],
)

a = Analysis(
    [SCRIPT],
    datas=[(ICON, ".")],                 # read at runtime for the window icon
    excludes=["unittest", "pydoc", "doctest", "pdb"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=NAME,
    icon=ICON,
    version=version_info,
    console=False,                       # a window app: no console window behind it
    disable_windowed_traceback=False,    # if startup ever fails, show the error in a dialog
    upx=False,                           # UPX-packed files trip antivirus heuristics more often
    strip=False,
    debug=False,
    runtime_tmpdir=None,
)
