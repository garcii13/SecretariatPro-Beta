"""Publish independent Live/Manager releases from verified platform artifacts."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import runpy

repo = os.environ['GH_REPO']
version = runpy.run_path('secretariat_core/release.py')['RELEASE_VERSION']
mac_live_only = os.environ.get('SP_RELEASE_SCOPE') == 'macos-live'
products = ('Live',) if mac_live_only else ('Live', 'Manager')
notes_path = 'docs/RELEASE_BETA8_MAC_LIVE.md'
def gh(*args):
    return subprocess.check_output(['gh', *args], text=True)

platforms = {'windows-2022': 'WINDOWS_RUN', 'macos-15': 'MACOS_ARM_RUN', 'macos-15-intel': 'MACOS_INTEL_RUN'}
if mac_live_only:
    platforms.pop('windows-2022')
# Reuse validated Windows binaries after Mac-only packaging fixes. Runtime,
# requirements, models, UI and every other application file must be unchanged.
allowed_changes = {'SecretariatPro_App.spec', 'SecretariatPro_OCR.spec',
                   '.github/workflows/publish-installers.yml', 'packaging/publish_installers.py',
                   notes_path, '.github/workflows/beta-installers.yml',
                   'packaging/smoke_macos.py'}
evidence = []
for platform, variable in platforms.items():
    run_id = os.environ[variable]
    if not run_id.isdigit():
        raise SystemExit('Invalid build run ID')
    run = json.loads(gh('api', f'repos/{repo}/actions/runs/{run_id}'))
    if run['path'] != '.github/workflows/beta-installers.yml':
        raise SystemExit('Unexpected build workflow')
    jobs = json.loads(gh('api', f'repos/{repo}/actions/runs/{run_id}/jobs'))['jobs']
    if not any(j['name'] == f'installers ({platform})' and j['conclusion'] == 'success' for j in jobs):
        raise SystemExit(f'{platform} did not pass all installer checks')
    if run['head_sha'] != os.environ['GITHUB_SHA']:
        comparison = json.loads(gh('api', f"repos/{repo}/compare/{run['head_sha']}...{os.environ['GITHUB_SHA']}"))
        changed = {entry['filename'] for entry in comparison['files']}
        if not changed.issubset(allowed_changes):
            raise SystemExit(f'Application source changed since {platform} was built: {changed - allowed_changes}')
    gh('run', 'download', run_id, '--name', f'SecretariatPro-beta-{platform}', '--dir', f'installers/{platform}')
    evidence.append(f"- {platform}: {run['html_url']} · `{run['head_sha']}`")

root = Path('installers')
installers = sorted(p for p in root.rglob('*') if p.suffix in ('.exe', '.dmg'))
suffixes = ('macos-arm64.dmg', 'macos-x86_64.dmg') if mac_live_only else ('windows-x64-setup.exe', 'macos-arm64.dmg', 'macos-x86_64.dmg')
expected = {f'SecretariatPro-{product}-{version}-{suffix}' for product in products for suffix in suffixes}
if {p.name for p in installers} != expected or len(installers) != len(expected):
    raise SystemExit('Unexpected installers for the selected release scope')
for path in installers:
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if path.with_suffix(path.suffix + '.sha256').read_text().split()[0] != digest:
        raise SystemExit(f'Checksum mismatch: {path.name}')

for product in products:
    files = []
    for path in installers:
        if path.name.startswith(f'SecretariatPro-{product}-'):
            files += [str(path), str(path.with_suffix(path.suffix + '.sha256'))]
    tag = f'{product.lower()}-v{version}'
    notes = Path(f'release-notes-{product}.md')
    notes.write_text(f'Release independiente de SecretariatPro {product}.\n\n' +
                     Path(notes_path).read_text() + '\n\nCompilaciones verificadas:\n\n' + '\n'.join(evidence))
    existing = subprocess.run(['gh', 'release', 'view', tag, '--json', 'isDraft'], capture_output=True, text=True)
    if existing.returncode == 0:
        if not json.loads(existing.stdout)['isDraft']:
            raise SystemExit(f'{tag} is already published; do not overwrite release assets')
        gh('release', 'upload', tag, '--clobber', *files)
    else:
        gh('release', 'create', tag, '--target', os.environ['GITHUB_SHA'], '--draft', '--prerelease',
           '--title', f'SecretariatPro {product} {version}', '--notes-file', str(notes), *files)
    gh('release', 'edit', tag, '--draft=false', '--prerelease')
    print(gh('release', 'view', tag, '--json', 'url', '--jq', '.url'))
