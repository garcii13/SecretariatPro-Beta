"""Audit installed build dependencies without adding the auditor to the product venv."""
import argparse
import importlib.metadata
from pathlib import Path
import subprocess
import sys
import tempfile
import venv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('release/dependency-audit.json'))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    installed = sorted({f"{item.metadata['Name']}=={item.version}" for item in importlib.metadata.distributions()})
    with tempfile.TemporaryDirectory(prefix='sp-dependency-audit-') as folder:
        root = Path(folder)
        requirements = root / 'installed.txt'
        requirements.write_text('\n'.join(installed) + '\n')
        venv.create(root / 'tool', with_pip=True)
        python = root / 'tool' / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
        subprocess.run([str(python), '-m', 'pip', 'install', '--quiet', 'pip-audit==2.10.1'], check=True)
        return subprocess.run([str(python), '-m', 'pip_audit', '--disable-pip', '--no-deps',
                               '-r', str(requirements), '--format', 'json', '--output', str(args.output.resolve())]).returncode


if __name__ == '__main__':
    raise SystemExit(main())
