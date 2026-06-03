# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 规格：前端 dist + contracts + FastAPI + 流程引擎 + Worker。"""

import os

from PyInstaller.utils.hooks import collect_submodules

spec_dir = os.path.dirname(os.path.abspath(SPEC))
repo_root = os.path.normpath(os.path.join(spec_dir, ".."))
backend_root = os.path.join(repo_root, "backend")

block_cipher = None

datas = [
    (os.path.join(repo_root, "frontend", "dist"), "frontend_dist"),
    (os.path.join(repo_root, "contracts"), "contracts"),
]

hiddenimports = (
    collect_submodules("app")
    + collect_submodules("bin")
    + [
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
    ]
)

a = Analysis(
    [os.path.join(backend_root, "desktop_entry.py")],
    pathex=[backend_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ScreenRPA",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.join(repo_root, "logo.ico"),
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ScreenRPA",
)
