#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "SecretariatPro · preparando entorno macOS estable"
echo "Python base: $($PYTHON_BIN -c 'import sys; print(sys.executable)')"
echo "Versión: $($PYTHON_BIN -c 'import platform; print(platform.python_version())')"
echo
echo "Recreando .venv para eliminar mezclas de Paddle/OpenCV..."
rm -rf .venv
"$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel

echo
echo "Instalando dependencias con constraints específicos de macOS..."
.venv/bin/python -m pip install -c constraints-macos.txt -r requirements.txt

echo
echo "Comprobando coherencia del entorno..."
.venv/bin/python -m pip check

.venv/bin/python - <<'PY2'
import platform
import cv2
import numpy
import paddle
import paddleocr
import joblib
import sklearn
import ocr_engine

print("Python:", platform.python_version())
print("Plataforma:", platform.platform())
print("NumPy:", numpy.__version__)
print("OpenCV:", cv2.__version__)
print("PaddlePaddle:", paddle.__version__)
print("PaddleOCR:", getattr(paddleocr, "__version__", "desconocida"))
print("joblib:", joblib.__version__)
print("scikit-learn:", sklearn.__version__)

errors = []
if not str(paddle.__version__).startswith("2.6.2"):
    errors.append(f"PaddlePaddle esperado 2.6.2; instalado {paddle.__version__}")
if not str(getattr(paddleocr, "__version__", "")).startswith("2.7.3"):
    errors.append(f"PaddleOCR esperado 2.7.3; instalado {getattr(paddleocr, '__version__', 'desconocida')}")
if str(cv2.__version__) != "4.6.0":
    errors.append(f"OpenCV esperado 4.6.0; instalado {cv2.__version__}")
if str(numpy.__version__) != "1.26.4":
    errors.append(f"NumPy esperado 1.26.4; instalado {numpy.__version__}")
if str(joblib.__version__) != "1.5.3":
    errors.append(f"joblib esperado 1.5.3; instalado {joblib.__version__}")
if str(sklearn.__version__) != "1.8.0":
    errors.append(f"scikit-learn esperado 1.8.0; instalado {sklearn.__version__}")

ocr_engine.configure(base_dir=".")
if ocr_engine._get_spocr() is None:
    errors.append("SP-OCR v0.7 no se pudo cargar: " + ocr_engine.active_model_info()["clock_hybrid_error"])
if ocr_engine._get_spscore() is None:
    errors.append("SP-SCORE v0.2 no se pudo cargar: " + ocr_engine.active_model_info()["score_hybrid_error"])
if errors:
    raise SystemExit("ERROR DE ENTORNO:\n- " + "\n- ".join(errors))
print("\nEntorno OCR macOS: OK")
PY2

echo
echo "Preparación completada."
echo "Arranca con: ./INICIAR_APP.command"
echo "En PyCharm usa: $(pwd)/.venv/bin/python"
