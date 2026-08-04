#!/usr/bin/env bash
# Build the CHD Risk Stratification macOS desktop app with PyInstaller.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  echo "[build] creating virtualenv..."
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip
fi
.venv/bin/pip install -e ".[ml,api]" pywebview pyinstaller

echo "[build] running PyInstaller..."
.venv/bin/python -m PyInstaller --noconfirm --clean chd_risk_desktop.spec

APP="dist/CHD Risk Stratification.app"
if [ ! -d "$APP" ]; then
  echo "[build] FAILED: app bundle not found" >&2
  exit 1
fi

mkdir -p release
ZIP="release/CHD-Risk-Stratification-macOS-arm64.zip"
rm -f "$ZIP"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$ZIP"
echo "[build] done: $ZIP ($(du -h "$ZIP" | cut -f1))"
echo "[build] app:   $APP"
