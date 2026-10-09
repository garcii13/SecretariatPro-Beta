import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "installer_assembly", Path(__file__).resolve().parents[1] / "packaging/assemble.py"
)
assembly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assembly)


class InstallerAssemblyTests(unittest.TestCase):
    def test_windows_version_accepts_beta_and_stable(self):
        self.assertEqual(assembly.windows_file_version("1.0.0-beta.9"), "1.0.0.9")
        self.assertEqual(assembly.windows_file_version("2.4.1"), "2.4.1.0")
        for invalid in ("1.0", "1.0.0/invalid", "1.0.65536", "1.0.0-beta.-1"):
            with self.subTest(version=invalid), self.assertRaises(ValueError):
                assembly.windows_file_version(invalid)

    def test_live_only_release_does_not_require_manager_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live = root / "dist/SecretariatPro Live"
            live.mkdir(parents=True)
            (root / "dist/SecretariatPro_OCR.exe").write_bytes(b"worker")
            expected = root / "release/SecretariatPro-Live-1.0.0-beta.9-windows-x64-setup.exe"

            def compile_installer(command, *, check):
                self.assertTrue(check)
                self.assertEqual(command[:4], ["compiler.exe", "/DProduct=Live",
                                               "/DVersion=1.0.0-beta.9", "/DFileVersion=1.0.0.9"])
                expected.write_bytes(b"installer")

            with patch.object(assembly.platform, "system", return_value="Windows"), \
                 patch.object(assembly.subprocess, "run", side_effect=compile_installer) as run:
                artifacts = assembly.assemble(root, version="1.0.0-beta.9",
                                              products=("Live",), compiler="compiler.exe")
            self.assertEqual(artifacts, [expected])
            self.assertEqual(run.call_count, 1)
            self.assertEqual((live / "SecretariatPro_OCR.exe").read_bytes(), b"worker")
            self.assertTrue(expected.with_suffix(".exe.sha256").is_file())


if __name__ == "__main__":
    unittest.main()
