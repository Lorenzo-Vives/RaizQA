# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['gui_raizQA_pyside.py'],
    pathex=[],
    binaries=[],
    datas=[('C:/RWD/qualian/models', 'models'), ('C:/RWD/qualian/code_viewer', 'code_viewer')],
    hiddenimports=[],
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
    name='gui_raizQA_pyside',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
