# PyInstaller spec file for building the PyQt6 GUI application.

block_cipher = None

import os
from PyInstaller.utils.hooks import collect_all

pyqt6 = collect_all('PyQt6')

a = Analysis(
    ['run_gui.py'],
    pathex=[],
    binaries=pyqt6[1],
    datas=
        pyqt6[0]
        + [
            ('configs', 'configs'),
            ('questions_config.json', '.'),
            ('prompts_config.json', '.'),
            ('litrx/prompts', 'litrx/prompts'),
        ],
    hiddenimports=pyqt6[2] + [
        'openai',
        'keyring.backends.Windows',
        'keyring.backends.macOS',
        'keyring.backends.SecretService',
        'yaml',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='LitRelevanceAI',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LitRelevanceAI'
)
