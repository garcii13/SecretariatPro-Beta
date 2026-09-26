"""Separate installed resources from persistent per-user data."""
import os
import sys
from pathlib import Path


def data_directory(resource_dir):
    if not getattr(sys, "frozen", False):
        return Path(resource_dir)
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    target = base / "SecretariatPro"
    target.mkdir(parents=True, exist_ok=True)
    return target
