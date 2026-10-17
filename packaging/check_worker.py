"""Exercise the frozen worker, including both bundled specialist models."""
import json
import argparse
import pathlib
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--worker", type=pathlib.Path)
args = parser.parse_args()
worker = args.worker or root / "dist" / ("SecretariatPro_OCR.exe" if sys.platform == "win32" else "SecretariatPro_OCR")
for option, expected in (("--diagnose-camera", "camera_runtime_ok"), ("--diagnose-window", "window_runtime_ok"), ("--diagnose-ocr", "ocr_runtime_ok")):
    result = subprocess.run([str(worker), option], capture_output=True, text=True, timeout=180)
    print(result.stdout)
    if result.returncode:
        print(result.stderr)
        raise SystemExit(f"Packaged worker failed: {option}")
    messages = []
    for line in result.stdout.splitlines():
        try:
            messages.append(json.loads(line.removeprefix("OCRMSG ")))
        except ValueError:
            pass
    if not any(isinstance(message, dict) and message.get("type") == expected for message in messages):
        raise SystemExit(f"Packaged worker did not confirm {expected}")
    if sys.platform == "win32" and option == "--diagnose-ocr":
        if not any(isinstance(message, dict) and message.get("type") == "ocr_inference_ok" for message in messages):
            raise SystemExit("Packaged Windows worker did not perform real OCR inference")
