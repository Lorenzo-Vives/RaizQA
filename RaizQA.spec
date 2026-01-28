from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all('PySide6')
spellchecker_datas, spellchecker_binaries, spellchecker_hiddenimports = collect_all('spellchecker')
openpyxl_datas, openpyxl_binaries, openpyxl_hiddenimports = collect_all('openpyxl')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=pyside6_binaries + spellchecker_binaries + openpyxl_binaries,
    datas=collect_data_files('pyspellchecker', includes=['resources/*']) + pyside6_datas + spellchecker_datas + openpyxl_datas + [
        ('gui', 'gui'),
        ('core', 'core'),
        ('code_viewer', 'code_viewer'),
        ('logo1.ico', '.'),
    ],
    hiddenimports=pyside6_hiddenimports + spellchecker_hiddenimports + openpyxl_hiddenimports,
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
    icon='logo1.ico',
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
