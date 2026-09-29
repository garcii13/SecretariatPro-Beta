"""Mount the generated DMGs and launch their copied applications on macOS CI."""
import json
import os
from pathlib import Path
import plistlib
import subprocess
import tempfile
import time
from urllib.request import urlopen

root = Path(__file__).resolve().parents[1]
if os.environ.get('CI') != 'true':
    raise SystemExit('Run on an isolated CI runner, not against user application data')
for product, port in (('Live', 18765), ('Manager', 18766)):
    images = list((root / 'release').glob(f'SecretariatPro-{product}-*-macos-*.dmg'))
    if len(images) != 1:
        raise SystemExit(f'Expected one DMG for {product}')
    with tempfile.TemporaryDirectory(prefix=f'sp-installed-{product}-') as directory:
        mount = plistlib.loads(subprocess.check_output(['hdiutil', 'attach', '-readonly', '-nobrowse', '-plist', str(images[0])]))
        volumes = [entry['mount-point'] for entry in mount['system-entities'] if 'mount-point' in entry]
        if len(volumes) != 1:
            raise SystemExit('Unexpected DMG volume layout')
        volume = Path(volumes[0])
        bundle = Path(directory) / f'SecretariatPro {product}.app'
        try:
            subprocess.run(['ditto', str(volume / bundle.name), str(bundle)], check=True)
        finally:
            subprocess.run(['hdiutil', 'detach', str(volume)], check=True)
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(bundle)], check=True)
        executable = bundle / 'Contents/MacOS' / f'SecretariatPro {product}'
        arguments = [str(executable), '--port', str(port)]
        if product == 'Live':
            arguments += ['--host', '127.0.0.1', '--windowed']
        log = root / 'release' / f'smoke-macos-{product}.log'
        with log.open('w') as output:
            app = subprocess.Popen(arguments, stdout=output, stderr=subprocess.STDOUT)
            try:
                health = None
                for _ in range(90):
                    if app.poll() is not None:
                        raise RuntimeError(f'{product} exited before startup: {log.read_text()}')
                    try:
                        with urlopen(f'http://127.0.0.1:{port}/api/health', timeout=2) as response:
                            health = json.load(response)
                        break
                    except OSError:
                        time.sleep(1)
                if not health:
                    raise RuntimeError(f'{product} backend did not start: {log.read_text()}')
                with urlopen(f'http://127.0.0.1:{port}/', timeout=5) as response:
                    if response.status != 200 or not response.read():
                        raise RuntimeError(f'{product} interface unavailable')
                time.sleep(5)
                if app.poll() is not None:
                    raise RuntimeError(f'{product} exited after opening: {log.read_text()}')
                if product == 'Live':
                    worker = executable.parent / 'SecretariatPro_OCR'
                    for option, expected in (('--diagnose-camera', 'camera_runtime_ok'), ('--diagnose-window', 'window_runtime_ok'), ('--diagnose-ocr', 'ocr_runtime_ok')):
                        result = subprocess.run([str(worker), option], capture_output=True, text=True, timeout=180)
                        print(result.stdout)
                        if result.returncode or f'"type": "{expected}"' not in result.stdout:
                            raise RuntimeError(f'Installed OCR failed: {result.stdout}\n{result.stderr}')
                print(f'PASS: mounted DMG, copied, verified signature and opened {product}; health={health}')
            finally:
                app.terminate()
                try:
                    app.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    app.kill()
                    app.wait()
