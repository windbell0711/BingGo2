# -*- mode: python ; coding: utf-8 -*-
# https://zhuanlan.zhihu.com/p/1987979560386576654

a = Analysis(
    ['main.py'],
    pathex=['D:/Documents/Coding/BingGo2'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'win32timezone',
    ],
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
    a.binaries,
    a.datas,
    [],
    name='BingGo_v2.0.0',  # Name
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='imgs/icon.ico',
)
