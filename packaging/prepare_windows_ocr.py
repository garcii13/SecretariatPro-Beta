"""Download and exercise the base recognizer before freezing Windows Live."""
from pathlib import Path
import os
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    if sys.platform != "win32":
        raise RuntimeError("This preparation is only for Windows")
    os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(ROOT / "build" / "paddlex-cache"))
    os.environ.setdefault("HF_HOME", str(ROOT / "build" / "huggingface-cache"))
    from paddleocr import TextRecognition
    from paddlex.utils.cache import CACHE_DIR
    from secretariat_core.windows_ocr import MODEL_NAME, verified_model_dir
    import cv2
    import numpy as np

    # PaddleX stores official downloaded models in its per-user cache.
    TextRecognition(model_name=MODEL_NAME, device="cpu", cpu_threads=1, enable_mkldnn=False)
    cache = Path(CACHE_DIR) / "official_models" / MODEL_NAME
    verified_model_dir(cache)
    target = ROOT / "models" / MODEL_NAME
    shutil.copytree(cache, target, dirs_exist_ok=True)
    model = TextRecognition(model_name=MODEL_NAME, model_dir=verified_model_dir(target),
                            device="cpu", cpu_threads=1, enable_mkldnn=False)
    image = np.full((96, 320, 3), 255, dtype=np.uint8)
    cv2.putText(image, "12:34", (12, 72), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    results = list(model.predict(input=image, batch_size=1))
    if not results:
        raise RuntimeError("The bundled recognizer produced no result")
    print(f"Prepared Windows recognizer: {target}")


if __name__ == "__main__":
    main()
