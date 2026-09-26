#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
PY=".venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "No existe .venv. Ejecuta primero PREPARAR_MAC_BETA.command"
  exit 1
fi
"$PY" - <<'PY'
import sys, platform
print("Python:", sys.executable)
print("Versión Python:", platform.python_version())
mods = {}
for name in ("numpy", "cv2", "paddle", "paddleocr", "joblib", "sklearn"):
    try:
        mod = __import__(name)
        mods[name] = mod
        print(f"{name}:", getattr(mod, "__version__", "sin __version__"))
    except Exception as exc:
        print(f"{name}: ERROR -> {exc}")
        raise SystemExit(2)
import ocr_engine
print("PaddleOCR major detectado:", ocr_engine._installed_paddleocr_major())
print("Apple Silicon Mac:", ocr_engine._is_apple_silicon_mac())
print("Backend esperado:", "v2_pipeline_mac_stable" if ocr_engine._installed_paddleocr_major() == 2 else "v3_text_recognition_mac_compat")
ocr_engine.configure(base_dir=".")
print("SP-OCR v0.7 cargado:", ocr_engine._get_spocr() is not None)
print("SP-SCORE v0.2 cargado:", ocr_engine._get_spscore() is not None)
print("Especialistas:", ocr_engine.active_model_info())
PY

echo
echo "pip check:"
"$PY" -m pip check
