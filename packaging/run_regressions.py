"""Run unittest cases and the existing zero-argument function regressions."""
import importlib
import inspect
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "tests"))
suite = unittest.defaultTestLoader.discover(str(root / "tests"))
for path in sorted((root / "tests").glob("test_*.py")):
    module = importlib.import_module(path.stem)
    for name, function in inspect.getmembers(module, inspect.isfunction):
        if name.startswith("test_") and function.__module__ == module.__name__:
            if inspect.signature(function).parameters:
                raise RuntimeError(f"Unsupported test parameters: {module.__name__}.{name}")
            suite.addTest(unittest.FunctionTestCase(function))
raise SystemExit(0 if unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful() else 1)
