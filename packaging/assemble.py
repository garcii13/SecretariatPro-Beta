"""Build independent Live and Manager installers from native bundles."""
from pathlib import Path
import hashlib
import platform
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0-beta.7"
PRODUCTS = ("Live", "Manager")


def assemble(root: Path = ROOT) -> list[Path]:
    dist, release = root / "dist", root / "release"
    release.mkdir(exist_ok=True)
    artifacts = []
    system = platform.system()
    if system not in ("Windows", "Darwin"):
        raise RuntimeError("Installers must be built on Windows or macOS")
    suffix = ".exe" if system == "Windows" else ""
    live = dist / ("SecretariatPro Live" if system == "Windows" else "SecretariatPro Live.app/Contents/MacOS")
    shutil.copy2(dist / f"SecretariatPro_OCR{suffix}", live / f"SecretariatPro_OCR{suffix}")
    for product in PRODUCTS:
        name = f"SecretariatPro {product}"
        if system == "Windows":
            iscc = shutil.which("iscc") or r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
            subprocess.run([iscc, f"/DProduct={product}", f"/DVersion={VERSION}", str(root / "packaging/windows.iss")], check=True)
            artifact = release / f"SecretariatPro-{product}-{VERSION}-windows-x64-setup.exe"
        else:
            bundle = dist / f"{name}.app"
            subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(bundle)], check=True)
            subprocess.run(["codesign", "--verify", "--deep", "--strict", str(bundle)], check=True)
            artifact = release / f"SecretariatPro-{product}-{VERSION}-macos-{platform.machine()}.dmg"
            with tempfile.TemporaryDirectory(prefix=f"dmg-{product}-", dir=dist) as directory:
                stage = Path(directory)
                subprocess.run(["ditto", str(bundle), str(stage / bundle.name)], check=True)
                (stage / "Applications").symlink_to("/Applications", target_is_directory=True)
                subprocess.run(["hdiutil", "create", "-volname", name, "-srcfolder", str(stage), "-ov", "-format", "UDZO", str(artifact)], check=True)
        if not artifact.is_file():
            raise RuntimeError(f"Installer missing: {artifact}")
        with artifact.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        artifact.with_suffix(artifact.suffix + ".sha256").write_text(f"{digest}  {artifact.name}\n", encoding="utf-8")
        artifacts.append(artifact)
    return artifacts


if __name__ == "__main__":
    for artifact in assemble():
        print(artifact)
