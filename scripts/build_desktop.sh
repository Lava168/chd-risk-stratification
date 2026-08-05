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

echo "[build] generating application icons..."
.venv/bin/python scripts/build_app_icons.py

echo "[build] running PyInstaller..."
.venv/bin/python -m PyInstaller --noconfirm --clean chd_risk_desktop.spec

APP="dist/CHD Risk Stratification.app"
if [ ! -d "$APP" ]; then
  echo "[build] FAILED: app bundle not found" >&2
  exit 1
fi

# macOS: repoint @rpath/libomp.dylib inside the frozen xgboost to the bundled
# libomp so the app works WITHOUT any DYLD_* env var at launch.
if [ "$(uname)" = "Darwin" ]; then
  XGB="$(find "$APP/Contents" -name "libxgboost.dylib" 2>/dev/null | head -1 || true)"
  LIBOMP="$(find "$APP/Contents" -name "libomp.dylib" 2>/dev/null | head -1 || true)"
  if [ -n "$XGB" ] && [ -n "$LIBOMP" ]; then
    echo "[build] repointing libomp inside frozen xgboost..."
    REL="$(python3 -c "import os;print(os.path.relpath('$LIBOMP', os.path.dirname('$XGB')))")"
    install_name_tool -change "@rpath/libomp.dylib" "@loader_path/$REL" "$XGB" || true
    codesign --force --sign - "$XGB" "$LIBOMP" 2>/dev/null || true
  else
    echo "[build] WARNING: libomp/libxgboost not found; packaged app may need DYLD_FALLBACK_LIBRARY_PATH at launch" >&2
  fi
fi

mkdir -p release
ZIP="release/CHD-Risk-Stratification-macOS-arm64.zip"
rm -f "$ZIP"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$ZIP"
echo "[build] done: $ZIP ($(du -h "$ZIP" | cut -f1))"
echo "[build] app:   $APP"
