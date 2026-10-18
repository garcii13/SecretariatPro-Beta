import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from secretariat_api import main as live
from manager_api import main as manager
from secretariat_core.local_access import trusted_request
from secretariat_api.runtime import ApplicationRuntime


class LocalAccessTests(unittest.TestCase):
    def test_live_and_manager_block_foreign_origin_and_host_before_side_effects(self):
        for module in (live, manager):
            client = TestClient(module.app, client=('127.0.0.1', 50100))
            for headers in ({'Origin': 'https://audit.invalid'}, {'Host': 'audit.invalid'},
                            {'Origin': 'null'}, {'Sec-Fetch-Site': 'cross-site'},
                            {'Origin': 'http://testserver:8766'}):
                with patch.object(module.runtime, 'logout') as logout:
                    self.assertEqual(client.post('/api/auth/logout', headers=headers).status_code, 403)
                    logout.assert_not_called()
            self.assertEqual(client.get('/api/health').status_code, 200)
            root = client.get('/')
            self.assertIn('no-store',root.headers['cache-control'])
            self.assertIn('HttpOnly',root.headers['set-cookie'])
            self.assertIn('SameSite=Strict',root.headers['set-cookie'])

    def test_websocket_rejects_foreign_origin_and_accepts_same_service(self):
        client = TestClient(live.app, client=('127.0.0.1', 50100))
        with patch.object(live.runtime, 'production_access_allowed', return_value=True), \
             patch.object(live.runtime, 'snapshot', return_value={'audit': 'synthetic-only'}):
            client.get('/api/health')
            for headers in ({'Origin': 'https://audit.invalid'}, {'Host': 'audit.invalid'}, {'Origin':'null'}):
                with self.assertRaises(WebSocketDisconnect) as exc:
                    with client.websocket_connect('/api/ws', headers=headers):
                        self.fail('Untrusted socket accepted')
                self.assertEqual(exc.exception.code, 4403)
            with client.websocket_connect('/api/ws', headers={'Origin': 'http://testserver'}) as ws:
                self.assertEqual(ws.receive_json()['payload'], {'audit': 'synthetic-only'})
            client.cookies.clear()
            with self.assertRaises(WebSocketDisconnect):
                with client.websocket_connect('/api/ws', headers={'Origin': 'http://testserver'}):
                    self.fail('Browser connected without its local session')

    def test_actual_lan_addresses_ports_ipv6_and_native_clients(self):
        def scope(host, origin=None, server=('192.168.1.2',8765), extra=()):
            return {'type':'http','scheme':'http','server':server,
                    'headers':[(b'host',host.encode()), *([(b'origin',origin.encode())] if origin else []), *extra]}
        self.assertTrue(trusted_request(scope('192.168.1.2:8765','http://192.168.1.2:8765')))
        self.assertTrue(trusted_request(scope('127.0.0.1:8765')))
        self.assertTrue(trusted_request(scope('[::1]:8765','http://[::1]:8765',('::1',8765))))
        self.assertFalse(trusted_request(scope('192.168.1.2:8766')))
        self.assertFalse(trusted_request(scope('attacker.invalid:8765')))
        self.assertFalse(trusted_request(scope('192.168.1.2:8765', extra=[(b'host',b'localhost:8765')])))

    def test_overlay_snapshot_is_immutable_match_bound_and_raw_scores_stay_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime = ApplicationRuntime(folder)
            runtime.active_workspace = {'id':'workspace'}
            runtime.active_match = {'id':'one'}
            runtime.score_store.write_external({'team1_score':'2','team2_score':'1','time':'12:34'})
            runtime.score_store.confirm_goal('team1_score')
            first = runtime.overlay_snapshot()
            self.assertEqual(first['overlay_transport']['scores']['team1_score'], '2')
            self.assertEqual(first['graphic_scores']['team1_score'], '3')
            runtime.active_match = {'id':'two'}
            second = runtime.overlay_snapshot()
            self.assertNotEqual(first['overlay_transport']['context'],second['overlay_transport']['context'])
            self.assertGreater(second['overlay_transport']['revision'],first['overlay_transport']['revision'])
            self.assertNotIn('overlay_transport',runtime.read_state())
