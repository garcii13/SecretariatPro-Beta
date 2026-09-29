"""Publish only the complete, successful native installer matrix."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

run_id = os.environ['BUILD_RUN_ID']
if not run_id.isdigit():
    raise SystemExit('Invalid build run ID')
repo = os.environ['GH_REPO']
def gh(*args):
    return subprocess.check_output(['gh', *args], text=True)

run = json.loads(gh('api', f'repos/{repo}/actions/runs/{run_id}'))
if run['conclusion'] != 'success' or run['path'] != '.github/workflows/beta-installers.yml':
    raise SystemExit('The complete installer workflow must pass before publication')
jobs = json.loads(gh('api', f'repos/{repo}/actions/runs/{run_id}/jobs'))['jobs']
required = {f'installers ({platform})' for platform in ('windows-2022', 'macos-15', 'macos-15-intel')}
if not required.issubset({j['name'] for j in jobs if j['conclusion'] == 'success'}):
    raise SystemExit('Missing a successful platform build')
if run['head_sha'] != os.environ['GITHUB_SHA']:
    raise SystemExit('Publish from the exact commit that was built')
gh('run', 'download', run_id, '--dir', 'installers')
root = Path('installers')
installers = sorted(p for p in root.rglob('*') if p.suffix in ('.exe', '.dmg'))
expected = {f'SecretariatPro-{product}-1.0.0-beta.6-{platform}'
            for product in ('Live', 'Manager')
            for platform in ('windows-x64-setup.exe', 'macos-arm64.dmg', 'macos-x86_64.dmg')}
if {p.name for p in installers} != expected or len(installers) != 6:
    raise SystemExit('Expected exactly the six independent installers')
files = []
for path in installers:
    checksum = path.with_suffix(path.suffix + '.sha256')
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if checksum.read_text().split()[0] != digest:
        raise SystemExit(f'Checksum mismatch: {path.name}')
    files += [str(path), str(checksum)]
tag = 'v1.0.0-beta.6'
gh('release', 'create', tag, '--target', run['head_sha'], '--prerelease',
   '--title', 'SecretariatPro Live y Manager 1.0.0 beta 6',
   '--notes-file', 'docs/RELEASE_BETA6.md', *files)
print(gh('release', 'view', tag, '--json', 'url', '--jq', '.url'))
