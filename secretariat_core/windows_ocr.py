"""Local recognizer assets for the Windows installer."""
from pathlib import Path

MODEL_NAME = "en_PP-OCRv4_mobile_rec"


def verified_model_dir(path):
    path = Path(path)
    required = ("inference.yml", "inference.pdiparams")
    if not all((path / name).is_file() for name in required):
        raise RuntimeError(f"Modelo PaddleOCR incompleto: {path}")
    if not any((path / name).is_file() for name in ("inference.json", "inference.pdmodel")):
        raise RuntimeError(f"Falta el grafo de inferencia PaddleOCR: {path}")
    return str(path)


def recognition_options(resource_dir, *, frozen):
    path = Path(resource_dir) / "models" / MODEL_NAME
    if path.exists() or frozen:
        return {"model_dir": verified_model_dir(path)}
    # Source development retains PaddleOCR's normal first-run download.
    return {}
