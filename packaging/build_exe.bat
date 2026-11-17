@echo off
rem Builds dist\SkyBlockConfigManager.exe, a portable .exe that runs without Python.
rem Building needs Python 3.8+ (python.org) once; double-click this file or run it from a prompt.
setlocal
cd /d "%~dp0.."

set "PY=python"
py -3 --version >nul 2>nul
if not errorlevel 1 set "PY=py -3"

echo Installing / updating PyInstaller...
%PY% -m pip install --upgrade "pyinstaller>=6"
if errorlevel 1 goto :fail

echo Building...
%PY% -m PyInstaller --noconfirm --clean packaging\SkyBlockConfigManager.spec
if errorlevel 1 goto :fail

echo.
echo Done: %CD%\dist\SkyBlockConfigManager.exe
pause
exit /b 0

:fail
echo.
echo Build failed - see the messages above.
pause
exit /b 1
