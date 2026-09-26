# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH)

datas = [
    (str(ROOT / "webapp"), "webapp"),
    (str(ROOT / "overlay.html"), "."),
    (str(ROOT / "script.js"), "."),
    (str(ROOT / "styles.css"), "."),
    (str(ROOT / "tablet"), "tablet"),
    (str(ROOT / "animations.json"), "."),

    (str(ROOT / "assets"), "assets"),
]
if (ROOT / "logos").exists():
    datas.append((str(ROOT / "logos"), "logos"))
if (ROOT / "models").exists():
    datas.append((str(ROOT / "models"), "models"))

hiddenimports = ["secretariat_api.main"]
if (ROOT / "public_config.json").exists():
    datas.append((str(ROOT / "public_config.json"), "."))
for package in ("uvicorn", "fastapi", "webview", "supabase", "paddleocr", "sklearn", "joblib", "imageio_ffmpeg", "AVFoundation"):
    try:
        hiddenimports += collect_submodules(package)
    except Exception:
        pass

# OCR libraries load models and modules dynamically.
for package in ("paddleocr", "sklearn", "joblib", "imageio_ffmpeg"):
    try:
        package_datas, package_bins, package_hidden = collect_all(package)
        datas += package_datas
        hiddenimports += package_hidden
    except Exception:
        pass

a = Analysis(
    [str(ROOT / "run_app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

icon_path = ROOT / "assets" / "secretariatpro.ico"
if not icon_path.exists():
    icon_path = ROOT / "assets" / "secretariatpro.png"

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SecretariatPro Live",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SecretariatPro Live",
)

# Build the app bundle only on macOS.
import sys
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="SecretariatPro Live.app",
        icon=str(ROOT / "assets" / "secretariatpro.png"),
        bundle_identifier="com.secretariatpro.app",
        info_plist={
            "NSCameraUsageDescription": "SecretariatPro utiliza la cámara seleccionada únicamente como fuente de vídeo para el OCR del marcador.",
            "NSCameraUseContinuityCameraDeviceType": True,
        },
    )
