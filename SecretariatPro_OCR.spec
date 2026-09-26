# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all
base = Path(SPECPATH)
datas = [(str(base / 'models'), 'models')]
binaries = []
hidden = []
for package in ('paddle', 'paddleocr', 'sklearn', 'joblib'):
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hidden += h
a = Analysis([str(base/'ocr_worker.py')], pathex=[str(base)], datas=datas, binaries=binaries, hiddenimports=hidden)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='SecretariatPro_OCR', console=True, upx=False)
