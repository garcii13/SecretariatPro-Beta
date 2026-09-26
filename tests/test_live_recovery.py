import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from secretariat_api.tablet_access import TabletAccess
from secretariat_core.services.replay_library import ReplayLibrary
from secretariat_core.services.replay_plugin_bridge import ReplayPluginBridge


class LiveRecoveryTests(unittest.TestCase):
    def test_multiple_qrs_one_use_each(self):
        access = TabletAccess()
        first, second = access.invite('scope'), access.invite('scope')
        for code in (first, second):
            _, token = access.pair(code, 'scope')
            self.assertTrue(access.authenticate(token, 'scope'))
            self.assertIsNone(access.authenticate(token, 'other'))
            with self.assertRaises(PermissionError):
                access.pair(code, 'scope')
        access.revoke_all()
        self.assertIsNone(access.authenticate(token, 'scope'))

    def test_twelve_events_and_match_isolation(self):
        with tempfile.TemporaryDirectory() as d:
            library = ReplayLibrary(d)
            for i in range(12):
                row = library.create_marker(match_id='one', label='Replay')
                library.update_marker(row['id'], 'one', label=f'Gol {i}')
            library.create_marker(match_id='two', label='other')
            self.assertEqual(len(library.snapshot('one')['clips']), 12)
            self.assertEqual(len(library.snapshot('two')['clips']), 1)
            with self.assertRaises(KeyError):
                library.update_marker(row['id'], 'two', label='wrong')
            payload = library.store.read({})
            payload['highlights'] = [{'id':'a','match_id':'one'}, {'id':'b','match_id':'two'}]
            library.store.write(payload)
            self.assertEqual([r['id'] for r in library.snapshot('one')['highlights']], ['a'])
            self.assertEqual(library.snapshot('')['highlights'], [])

    def test_migration_keeps_original(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            lib = ReplayLibrary(root/'runtime')
            video = lib.exports_dir/'test.mp4'
            video.write_bytes(b'video')
            lib.store.write({'clips':[], 'highlights':[{'id':'a','match_id':'match','path':str(video)}]})
            migrated = ReplayLibrary(root/'runtime', root/'Repeticiones')
            target = Path(migrated.snapshot('match')['highlights'][0]['path'])
            self.assertEqual(target.parent, (root/'Repeticiones'/'match').resolve())
            self.assertEqual(target.read_bytes(), video.read_bytes())

    def test_old_plugin_error_does_not_cancel_new_capture(self):
        bridge = ReplayPluginBridge(SimpleNamespace(connected=True))
        old = {'available':True, 'buffers_active':True, 'event_serial':5, 'error':'previous failure'}
        ready = {**old, 'event_serial':6, 'error':'', 'event_ready':True, 'saved_paths':[{'path':'new'}]}
        with patch.object(bridge, 'status', side_effect=[old, old, ready]), patch.object(bridge, '_trigger') as trigger, patch('time.sleep'):
            self.assertEqual(bridge.mark()['event_serial'], 6)
            trigger.assert_called_once_with('mark')

    def test_video_preview_does_not_block_hotkeys(self):
        import threading
        from unittest.mock import Mock
        from obs_controller import OBSController
        control = OBSController()
        control.connected = True
        control._client = Mock()
        control._program_scene_name = 'Live'
        entered, release, commanded = threading.Event(), threading.Event(), threading.Event()
        def frame(*args, **kwargs):
            entered.set()
            release.wait(2)
            return b'frame'
        control._preview = SimpleNamespace(connected=True, screenshot=frame)
        preview = threading.Thread(target=control.program_screenshot)
        preview.start()
        try:
            self.assertTrue(entered.wait(1))
            def command():
                control.trigger_hotkey_by_name('mark')
                commanded.set()
            worker = threading.Thread(target=command)
            worker.start()
            self.assertTrue(commanded.wait(.5), 'Control waited for the video preview')
        finally:
            release.set()
            preview.join(2)
        worker.join(2)
