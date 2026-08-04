@echo off
REM Build the CHD Risk Stratification desktop app on Windows.
REM Usage: double-click, or run from cmd: scripts\build_desktop.bat
setlocal
cd /d "%~dp0.."

if not exist .venv (
  echo [build] creating virtualenv...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -e ".[ml,api]" pywebview pyinstaller

echo [build] running PyInstaller...
python -m PyInstaller --noconfirm --clean chd_risk_desktop.spec

if not exist "dist\CHD Risk Stratification" (
  echo [build] FAILED: output not found
  exit /b 1
)

echo [build] done: dist\CHD Risk Stratification\CHD Risk Stratification.exe
echo [build] Copy the folder, or zip it, to distribute on Windows.
endlocal
