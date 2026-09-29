# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import platform
import subprocess
import sys
import importlib.util
from PyInstaller.utils.hooks import collect_all, copy_metadata
base = Path(SPECPATH)
datas = [(str(base / 'models'), 'models')]
if sys.platform == 'darwin':
    datas += copy_metadata('paddleocr', recursive=True)
binaries = []
hidden = []
search_paths = [str(base)]
if sys.platform == 'darwin':
    # PaddleOCR 2.x imports these packages without the paddleocr prefix.
    # Analyze their real imports so native dependencies (e.g. pyclipper) ship.
    ocr_package = Path(next(iter(importlib.util.find_spec('paddleocr').submodule_search_locations)))
    # Resolve the paddleocr package before its same-named internal module.
    search_paths += [str(ocr_package.parent), str(ocr_package)]
    # Legacy modules derive sys.path and resource paths from __file__.
    # Preserve source trees at their unprefixed import locations as well.
    datas += [(str(ocr_package / name), name) for name in ('ppocr', 'tools', 'ppstructure')]
    hidden += ['ppocr.postprocess', 'ppocr.data', 'tools.infer.predict_system', 'ppstructure.predict_system']
for package in ('paddle', 'paddleocr', 'sklearn', 'joblib'):
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hidden += h
# Paddle 2.6.2's macOS wheel contains Intel-only helper libraries even on
# Apple Silicon. Explicit collect_all entries bypass PyInstaller's usual
# dependency architecture checks and can shadow NumPy's native libraries.
if sys.platform == 'darwin':
    native_binaries = []
    for source, destination in binaries:
        result = subprocess.run(['lipo', '-archs', source], capture_output=True, text=True)
        if result.returncode == 0 and platform.machine() not in result.stdout.split():
            print(f'Excluded incompatible library: {source}')
            continue
        native_binaries.append((source, destination))
    binaries = native_binaries

a = Analysis([str(base/'ocr_worker.py')], pathex=search_paths, datas=datas, binaries=binaries, hiddenimports=hidden,
             runtime_hooks=[str(base/'packaging/rthook_paddle.py')])
# collect_all also returns .dylib files as data, which Analysis reclassifies.
# Replace any remaining foreign-architecture helpers with the matching native
# NumPy helper; exclude unused foreign libraries without a native equivalent.
if sys.platform == 'darwin':
    import numpy
    native_libs = Path(numpy.__file__).parent / '.dylibs'
    fixed = []
    for destination, source, kind in a.binaries:
        if kind == 'BINARY' and source.endswith('.dylib'):
            result = subprocess.run(['lipo', '-archs', source], capture_output=True, text=True)
            if result.returncode == 0 and platform.machine() not in result.stdout.split():
                replacement = native_libs / Path(source).name
                if not replacement.is_file():
                    continue
                check = subprocess.run(['lipo', '-archs', str(replacement)], capture_output=True, text=True)
                if check.returncode or platform.machine() not in check.stdout.split():
                    raise RuntimeError(f'No native replacement for {source}')
                source = str(replacement)
        fixed.append((destination, source, kind))
    a.binaries = fixed
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='SecretariatPro_OCR', console=True, upx=False)
