"""In-memory ASGI probe: no real server, cloud access or production state mutations."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from unittest.mock import patch
from fastapi.testclient import TestClient
from secretariat_api import main as live
from manager_api import main as manager

with patch.object(live.runtime, 'production_access_allowed', return_value=True), \
     patch.object(live.runtime, 'snapshot', return_value={'audit': 'synthetic-only'}):
    client = TestClient(live.app, client=('127.0.0.1', 50200))
    with client.websocket_connect('/api/ws', headers={
        'Origin': 'https://audit.invalid', 'Host': 'audit.invalid'
    }) as ws:
        print('LIVE_WS_UNTRUSTED_ORIGIN:', ws.receive_json())
with patch.object(manager.runtime, 'state', return_value={'audit': 'synthetic-only'}):
    client = TestClient(manager.app, client=('127.0.0.1', 50200))
    response = client.get('/api/state', headers={
        'Origin': 'https://audit.invalid', 'Host': 'audit.invalid'
    })
    print('MANAGER_UNTRUSTED_HOST:', response.status_code, response.json())
