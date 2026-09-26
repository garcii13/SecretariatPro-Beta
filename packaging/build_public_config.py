"""Export only the intentionally distributable Supabase endpoint and anon key."""
import base64
import json
import os
from pathlib import Path
from dotenv import dotenv_values
root = Path(__file__).resolve().parents[1]
values = {**dotenv_values(root / '.env'), **os.environ}
url = values.get('SUPABASE_URL', '')
key = values.get('SUPABASE_PUBLISHABLE_KEY') or values.get('SUPABASE_ANON_KEY', '')
existing_path = root / 'public_config.json'
existing = json.loads(existing_path.read_text(encoding='utf-8')) if existing_path.exists() else {}
profile_portal_url = values.get('SUPABASE_PROFILE_PORTAL_URL') or existing.get('SUPABASE_PROFILE_PORTAL_URL', '')
if not url.startswith('https://') or not key:
    raise SystemExit('Configure SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY')
if not key.startswith('sb_publishable_'):
    try:
        encoded = key.split('.')[1]
        role = json.loads(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)))['role']
    except Exception:
        raise SystemExit('Unrecognized key: refusing to package it')
    if role != 'anon':
        raise SystemExit('Only publishable/anon keys may be distributed')
payload = {'SUPABASE_URL': url, 'SUPABASE_PUBLISHABLE_KEY': key}
if profile_portal_url:
    if not str(profile_portal_url).startswith('https://'):
        raise SystemExit('SUPABASE_PROFILE_PORTAL_URL must use HTTPS')
    payload['SUPABASE_PROFILE_PORTAL_URL'] = str(profile_portal_url)
(root / 'public_config.json').write_text(json.dumps(payload, indent=2) + '\n')
print('Public configuration exported; no service credentials included.')
