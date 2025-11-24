# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Empaquetado para macOS en formato .app
a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=collect_data_files('pyspellchecker', includes=['resources/*']) + [
        ('gui', 'gui'),
        ('core', 'core'),
        ('code_viewer', 'code_viewer'),
        ('data', 'data'),
        ('models', 'models'),
        ('memos', 'memos'),
    ],
    hiddenimports=[],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='RaizQA',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Genera el bundle .app (dist/RaizQA.app)
app = BUNDLE(
    exe,
    name='RaizQA.app',
    icon=None,  # Reemplaza con una ruta .icns si la tienes, por ejemplo 'raizqa.icns'
    bundle_identifier='com.raizqa.app',
)
