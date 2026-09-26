# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_submodules
base = Path(SPECPATH)
datas = [(str(base / 'manager_app'), 'manager_app'), (str(base / 'assets'), 'assets')]
if (base / 'public_config.json').exists():
    datas.append((str(base / 'public_config.json'), '.'))
hiddenimports = ['manager_api.main', 'supabase', 'webview', 'openpyxl', 'multipart', 'dotenv'] + collect_submodules('uvicorn') + collect_submodules('webview')
a = Analysis([str(base/'run_manager.py')], pathex=[str(base)], binaries=[], datas=datas, hiddenimports=hiddenimports, hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='SecretariatPro Manager', debug=False, strip=False, upx=False, console=False, icon=str(base/'assets'/'manager_icon.ico'))
coll = COLLECT(exe, a.binaries, a.datas, name='SecretariatPro Manager')
if sys.platform == 'darwin':
    app = BUNDLE(coll, name='SecretariatPro Manager.app', icon=str(base/'assets'/'manager_icon.png'), bundle_identifier='com.secretariatpro.manager')
