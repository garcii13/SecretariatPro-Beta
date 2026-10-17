"""Build independent Live and Manager installers from native bundles."""
from pathlib import Path
import argparse
import hashlib
import platform
import re
import shutil
import subprocess
import tempfile
import os
import runpy

ROOT = Path(__file__).resolve().parents[1]
VERSION = runpy.run_path(str(ROOT / 'secretariat_core/release.py'))['RELEASE_VERSION']
PRODUCTS = ("Live",) if os.environ.get("SP_BUILD_PRODUCT") == "Live" else ("Live", "Manager")


def windows_file_version(version: str) -> str:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:-beta\.(\d+))?", version)
    if not match:
        raise ValueError("Expected a version such as 1.0.0-beta.9")
    numbers = [int(value or 0) for value in match.groups()]
    if any(value > 65535 for value in numbers):
        raise ValueError("Windows version components must not exceed 65535")
    return ".".join(map(str, numbers))


def assemble(root: Path = ROOT, *, version: str = VERSION,
             products=PRODUCTS, compiler: str | None = None) -> list[Path]:
    file_version = windows_file_version(version)
    if not products or any(product not in PRODUCTS for product in products):
        raise ValueError("Choose Live or Manager")
    dist, release = root / "dist", root / "release"
    release.mkdir(exist_ok=True)
    artifacts = []
    system = platform.system()
    if system not in ("Windows", "Darwin"):
        raise RuntimeError("Installers must be built on Windows or macOS")
    suffix = ".exe" if system == "Windows" else ""
    live = dist / ("SecretariatPro Live" if system == "Windows" else "SecretariatPro Live.app/Contents/MacOS")
    if "Live" in products:
        shutil.copy2(dist / f"SecretariatPro_OCR{suffix}", live / f"SecretariatPro_OCR{suffix}")
    for product in products:
        name = f"SecretariatPro {product}"
        if system == "Windows":
            iscc = compiler or shutil.which("iscc") or r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
            subprocess.run([iscc, f"/DProduct={product}", f"/DVersion={version}", f"/DFileVersion={file_version}", str(root / "packaging/windows.iss")], check=True)
            artifact = release / f"SecretariatPro-{product}-{version}-windows-x64-setup.exe"
        else:
            bundle = dist / f"{name}.app"
            subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(bundle)], check=True)
            subprocess.run(["codesign", "--verify", "--deep", "--strict", str(bundle)], check=True)
            artifact = release / f"SecretariatPro-{product}-{version}-macos-{platform.machine()}.dmg"
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=VERSION)
    parser.add_argument("--product", action="append", choices=PRODUCTS)
    parser.add_argument("--compiler", help="Path to the Inno Setup compiler")
    args = parser.parse_args()
    for artifact in assemble(version=args.version, products=args.product or PRODUCTS, compiler=args.compiler):
        print(artifact)
