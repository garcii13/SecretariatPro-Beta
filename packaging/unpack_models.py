"""Restore and verify the released OCR models used by native builds."""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_NAME = "secretariatpro-ocr-models-v0.7-v0.2.zip"
MODEL_KEYS = ("clock", "scores")


def unpack_models(root: Path = ROOT, archive: Path | None = None) -> list[str]:
    archive = archive or root / ARCHIVE_NAME
    manifest = json.loads((root / "models" / "MANIFEST_SP_OCR.json").read_text(encoding="utf-8"))
    expected = {
        f"models/{manifest[key]['file']}": str(manifest[key]["sha256"])
        for key in MODEL_KEYS
    }
    restored: list[str] = []
    with zipfile.ZipFile(archive) as bundle:
        available = set(bundle.namelist())
        missing = set(expected) - available
        if missing:
            raise ValueError(f"OCR model bundle is incomplete: {', '.join(sorted(missing))}")
        for name, digest in expected.items():
            payload = bundle.read(name)
            if hashlib.sha256(payload).hexdigest() != digest:
                raise ValueError(f"OCR model checksum mismatch: {name}")
            target = (root / name).resolve()
            if not target.is_relative_to((root / "models").resolve()):
                raise ValueError("Unsafe OCR model path")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            restored.append(name)
    return restored


if __name__ == "__main__":
    supplied = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
    print("Restored verified models:", ", ".join(unpack_models(archive=supplied)))
