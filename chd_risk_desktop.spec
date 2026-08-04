# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: build the CHD Risk Stratification desktop app.

Cross-platform: macOS produces CHD Risk Stratification.app, Windows produces
dist/CHD Risk Stratification/ with CHD Risk Stratification.exe.
The trained model bundle is included only when present (git-ignored); without it
the app falls back to the weighted prototype at runtime.
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.loops.uvloop",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "uvicorn.middleware",
    "uvicorn.middleware.proxy_headers",
    "uvicorn.middleware.wsgi",
    "xgboost",
    "shap",
    "numba",
    "llvmlite",
    "llvmlite.binding",
] + collect_submodules("chd_risk")

# ---- platform-specific native libs ----
import xgboost  # noqa: E402  (installed on the build machine)

XGB_DIR = Path(xgboost.__file__).resolve().parent
binaries = []
if sys.platform == "darwin":
    xgb_lib = XGB_DIR / "lib" / "libxgboost.dylib"
    libomp = Path(".venv/lib/libomp/libomp.dylib")
    if libomp.exists():
        binaries.append((str(libomp), "libomp"))
elif sys.platform == "win32":
    xgb_lib = XGB_DIR / "lib" / "xgboost.dll"
else:  # linux
    xgb_lib = XGB_DIR / "lib" / "libxgboost.so"
if xgb_lib.exists():
    binaries.append((str(xgb_lib), "xgboost/lib"))
version_file = XGB_DIR / "VERSION"
if version_file.exists():
    binaries.append((str(version_file), "xgboost"))

# ---- optional trained model bundle ----
datas = [("ui", "ui")]
model_bundle = Path("models/trained_model_bundle.joblib")
if model_bundle.exists():
    datas.append((str(model_bundle), "models"))

a = Analysis(
    ["desktop.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CHD Risk Stratification",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="CHD Risk Stratification",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="CHD Risk Stratification.app",
        icon=None,
        bundle_identifier="com.chd.riskstratification",
        info_plist={
            "CFBundleShortVersionString": "0.1.0",
            "CFBundleVersion": "0.1.0",
            "NSHighResolutionCapable": True,
        },
    )
