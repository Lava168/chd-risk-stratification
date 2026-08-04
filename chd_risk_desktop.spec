# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: build the CHD Risk Stratification desktop app (macOS)."""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = [
    # uvicorn dynamically imports its loops/protocols
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
    # model runtime: xgboost (via joblib pickle), shap (explanations), numba/llvmlite
    "xgboost",
    "shap",
    "numba",
    "llvmlite",
    "llvmlite.binding",
] + collect_submodules("chd_risk")

a = Analysis(
    ["desktop.py"],
    pathex=["."],
    binaries=[
        # xgboost has no PyInstaller hook; its native lib must be placed where
        # xgboost.libpath looks: <sys.base_prefix>/xgboost/lib/libxgboost.dylib
        (".venv/lib/python3.9/site-packages/xgboost/lib/libxgboost.dylib", "xgboost/lib"),
        # xgboost.core reads VERSION from the package dir at import time.
        (".venv/lib/python3.9/site-packages/xgboost/VERSION", "xgboost"),
    ],
    datas=[
        ("ui", "ui"),
        ("models/trained_model_bundle.joblib", "models"),
        (".venv/lib/libomp/libomp.dylib", "libomp"),
    ],
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
