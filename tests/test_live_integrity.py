"""Real persistence and score recovery, with only disk/network faults injected."""
import errno
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient
from secretariat_api import main
from secretariat_api.runtime import ApplicationRuntime
from secretariat_core.json_store import JSONStore, LiveJSONStore
from secretariat_core.ocr_store import ScoreFileStore
from secretariat_core.services.replay_library import ReplayLibrary
from secretariat_core.services.broadcast_flow import BroadcastFlow
from supabase_client import ScoreboardSupabaseClient


FULL = OSError(errno.ENOSPC, 'No space left on device')


class DiskRecoveryTests(unittest.TestCase):
    def test_atomic_disk_full_keeps_old_file_and_live_state_recovers(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LiveJSONStore(Path(folder) / 'state.json')
            store.write({'score': 2})
            with patch('secretariat_core.json_store.os.fsync', side_effect=FULL):
                store.write({'score': 3})
                store.update({}, lambda state: state.update(score=4))
                self.assertEqual(store.read({}), {'score': 4})
                self.assertEqual(json.loads(store.path.read_text()), {'score': 2})
                self.assertTrue(store.pending_persistence)
            with patch('secretariat_core.json_store.time.monotonic', return_value=float('inf')):
                self.assertEqual(store.read({}), {'score': 4})
            self.assertFalse(store.pending_persistence)
            self.assertEqual(json.loads(store.path.read_text()), {'score': 4})
            self.assertEqual(list(Path(folder).glob('*.tmp')), [])

    def test_regular_settings_store_never_claims_a_failed_write_succeeded(self):
        with tempfile.TemporaryDirectory() as folder:
            store = JSONStore(Path(folder) / 'settings.json')
            with patch('secretariat_core.json_store.tempfile.mkstemp', side_effect=FULL):
                with self.assertRaises(OSError): store.write({'setting': 'new'})

    def test_permissions_are_not_treated_as_disk_full(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LiveJSONStore(Path(folder) / 'state.json')
            with patch('secretariat_core.json_store.tempfile.mkstemp', side_effect=PermissionError('denied')):
                with self.assertRaises(PermissionError): store.write({'score': 3})
            self.assertFalse(store.pending_persistence)

    def test_manual_score_recovers_on_read_without_another_goal_or_ocr_write(self):
        with tempfile.TemporaryDirectory() as folder:
            store=ScoreFileStore(folder)
            with patch.object(store,'_atomic_write',side_effect=FULL):
                store.write_readings({'team1_score':3,'time':'12:34'})
            with patch('secretariat_core.ocr_store.time.monotonic',return_value=float('inf')):
                self.assertEqual(store.read('team1_score'),'3')
            self.assertFalse(store._pending_readings)
            self.assertEqual((Path(folder)/'Time.txt').read_text(),'12:34')

    def test_live_http_and_overlay_keep_working_with_full_disk_and_replay_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime = ApplicationRuntime(folder)
            try:
                runtime.score_store.write_external({'team1_score':'2','team2_score':'1','time':'12:34'})
                with patch.object(main, 'runtime', runtime), patch.object(runtime, 'production_access_allowed', return_value=True), \
                     patch('secretariat_core.json_store.tempfile.mkstemp', side_effect=FULL), \
                     patch.object(runtime.score_store, '_atomic_write', side_effect=FULL), \
                     patch.object(runtime, '_replay_snapshot', side_effect=FULL):
                    runtime.mutate_state(lambda state: state['match'].update(period=2))
                    runtime.score_store.write_external({'time':'12:35'})
                    client = TestClient(main.app, client=('127.0.0.1',50100))
                    state = client.get('/api/state')
                    self.assertEqual(state.status_code,200)
                    self.assertTrue(state.json()['storage_health']['pending_persistence'])
                    self.assertEqual(state.json()['state']['match']['period'],2)
                    self.assertEqual(client.get('/scores/Time.txt').text,'12:35')
                    self.assertEqual(client.get('/data.json').json()['match']['period'],2)
                    self.assertEqual(client.get('/api/live').status_code,200)
                runtime.score_store.write_readings({'time':'12:35'})
                self.assertEqual((runtime.paths.scores_dir/'Time.txt').read_text(),'12:35')
                self.assertFalse(runtime.score_store._pending_readings)
            finally: runtime.shutdown()

    def test_successful_online_entitlement_survives_offline_cache_write_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime=ApplicationRuntime(folder)
            try:
                runtime.supabase=SimpleNamespace(user_id='user',latest_workspace_subscription=lambda _: {'status':'active'})
                runtime.active_workspace={'id':'ws'}
                with patch.object(runtime.subscription_store,'save',side_effect=FULL), patch.object(runtime.subscription_store,'offline_access') as offline:
                    self.assertTrue(runtime.refresh_subscription_access(force=True)['allowed'])
                    offline.assert_not_called()
                runtime.supabase.latest_workspace_subscription=lambda _: {'status':'suspended'}
                with patch.object(runtime.subscription_store,'save',side_effect=FULL):
                    self.assertFalse(runtime.refresh_subscription_access(force=True)['allowed'])
            finally: runtime.shutdown()


class EventScoreTests(unittest.TestCase):
    def test_retries_delete_edit_and_real_goals_with_same_clock(self):
        with tempfile.TemporaryDirectory() as folder:
            store=ScoreFileStore(folder)
            store.correct_score('team1_score',2); store.correct_score('team2_score',1)
            store.reconcile_event_goals({'old':'team1_score'},seed=True)
            self.assertEqual(store.confirm_goal('team1_score',2,'new'),3)
            self.assertEqual(store.confirm_goal('team1_score',2,'new'),3)
            store.write_readings({'team1_score':3})
            store.reconcile_event_goals({'old':'team1_score','new':'team1_score'},manual=True)
            # Removing a duplicate subtracts exactly one, leaving the manual offset.
            store.reconcile_event_goals({'old':'team1_score'},manual=True)
            store.reconcile_event_goals({'old':'team1_score'},manual=True)
            self.assertEqual(store.read('team1_score'),'2')
            # Moving the goal to the other side corrects both counters.
            store.reconcile_event_goals({'old':'team2_score'},manual=True)
            self.assertEqual(store.read('team1_score'),'1'); self.assertEqual(store.read('team2_score'),'2')
            # A different request ID is a real second goal, even at the same time.
            self.assertEqual(store.confirm_goal('team2_score',2,'another'),3)
            reloaded=ScoreFileStore(folder)
            self.assertEqual(reloaded.confirm_goal('team2_score',2,'another'),3)

    def test_deletion_releases_confirmed_floor_without_rewriting_ocr(self):
        with tempfile.TemporaryDirectory() as folder:
            store=ScoreFileStore(folder)
            store.write_external({'team1_score':'2'})
            store.reconcile_event_goals({},seed=True)
            store.confirm_goal('team1_score',2,'g')
            store.reconcile_event_goals({})
            self.assertEqual(store.read('team1_score'),'2')
            self.assertEqual(store.reconciliation()['team1_score']['floor'],2)
            store.write_external({'team1_score':'2'})
            self.assertEqual(store.reconciliation()['team1_score']['internal'],2)

    def test_reload_of_act_does_not_confirm_an_existing_goal_twice(self):
        with tempfile.TemporaryDirectory() as folder:
            store=ScoreFileStore(folder); store.correct_score('team1_score',3)
            store.reset_reconciliation(); store.reconcile_event_goals({'g':'team1_score'},seed=True)
            self.assertEqual(store.confirm_goal('team1_score',2,'g'),3)

    def test_client_keeps_same_database_id_across_restarts_and_separates_accounts(self):
        client=object.__new__(ScoreboardSupabaseClient)
        client.user=SimpleNamespace(id='one'); client.client=Mock()
        client.client.rpc.return_value.execute.return_value.data={'event':{'id':'goal'},'assist':None,'created':True}
        payload=dict(match_id='m',team_id='h',scorer_id='p',assistant_id=None,request_id='streamdeck-press')
        client.create_goal_with_assist(**payload)
        first=client.client.rpc.call_args.args[1]['p_event_id']
        client.create_goal_with_assist(**payload)
        self.assertEqual(client.client.rpc.call_args.args[1]['p_event_id'],first)
        client.user=SimpleNamespace(id='two');client.create_goal_with_assist(**payload)
        self.assertNotEqual(client.client.rpc.call_args.args[1]['p_event_id'],first)


class ReplayStorageTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name);self.library=ReplayLibrary(self.root/'library')

    def test_snapshot_is_read_only_even_when_directories_cannot_be_created(self):
        with patch.object(Path,'mkdir',side_effect=FULL):
            self.assertIn('videos_directory',self.library.snapshot('new-match'))

    def test_low_disk_refuses_capture_without_removing_pending_or_exported_media(self):
        source=self.root/'original.mkv';source.write_bytes(b'video')
        marker=self.library.create_marker(match_id='m',label='Gol')
        with patch('secretariat_core.services.replay_library.shutil.disk_usage',return_value=SimpleNamespace(free=1024)):
            with self.assertRaisesRegex(RuntimeError,'Espacio insuficiente'):
                self.library.complete_multicam_marker(marker['id'],[str(source)])
        self.assertEqual(source.read_bytes(),b'video')
        self.assertEqual(self.library.snapshot('m')['clips'][0]['status'],'pending')

    def test_hardlink_archives_survive_obs_cleanup_and_cache_limit_keeps_unsaved_marks(self):
        source=self.root/'camera.mkv';source.write_bytes(b'original')
        marker=self.library.create_marker(match_id='m',label='Gol')
        with patch('secretariat_core.services.replay_library.shutil.disk_usage',return_value=SimpleNamespace(free=32*1024**3)):
            clip=self.library.complete_multicam_marker(marker['id'],[str(source)])
            self.assertTrue(source.samefile(clip['path']))
            source.unlink()
            self.assertEqual(Path(clip['path']).read_bytes(),b'original')
            self.library.max_cache_bytes=1
            with self.assertRaisesRegex(RuntimeError,'límite'):self.library.prepare_capture()
            self.assertTrue(Path(clip['path']).is_file())

    def test_cache_prunes_only_exported_old_angles_and_preserves_videos_and_newest_mark(self):
        with patch('secretariat_core.services.replay_library.shutil.disk_usage',return_value=SimpleNamespace(free=32*1024**3)):
            clips=[]
            for n in range(3):
                source=self.root/f'camera{n}.mkv';source.write_bytes(b'video')
                mark=self.library.create_marker(match_id='m',label='Gol')
                clips.append(self.library.complete_multicam_marker(mark['id'],[str(source)]))
            video=self.library.exports_dir/'saved.mp4';video.write_bytes(b'finished')
            self.library.store.update({},lambda data:data.update(highlights=[{'id':'saved','match_id':'m','path':str(video),'clip_ids':[clips[0]['id']]}]))
            self.library.max_cache_bytes=11
            self.library.prepare_capture()
            self.assertFalse(Path(clips[0]['path']).exists())
            self.assertTrue(Path(clips[1]['path']).is_file())
            self.assertTrue(Path(clips[2]['path']).is_file())
            self.assertEqual(video.read_bytes(),b'finished')

    def test_changing_volume_keeps_old_library_and_persists_configuration(self):
        destination=self.root/'external';destination.mkdir()
        old=self.library.exports_dir/'saved.mp4';old.write_bytes(b'finished')
        self.library.store.write({'clips':[],'highlights':[{'id':'saved','match_id':'m','path':str(old)}]})
        self.library.configure_storage(str(destination),4)
        self.assertEqual(self.library.snapshot('m')['highlights'][0]['path'],str(old))
        reloaded=ReplayLibrary(self.root/'library')
        self.assertEqual(reloaded.exports_dir,(destination/'Repeticiones').resolve())
        self.assertEqual(reloaded.max_cache_bytes,4*1024**3)



class BroadcastCorrectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_old_goal_correction_does_not_cancel_new_goal_waiting_for_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime=ApplicationRuntime(folder)
            try:
                flow=BroadcastFlow(runtime,AsyncMock())
                runtime.mutate_state(lambda state: state['bottombar'].update(event_id='old',status='show'))
                await flow.begin({'event_id':'new','scorer':'Current'})
                generation=flow.generation
                await flow.correct_event('old')
                self.assertEqual(flow.generation,generation)
                self.assertEqual(runtime.read_state()['pending_goal_celebration']['event_id'],'new')
            finally: runtime.shutdown()

    async def test_correcting_pending_goal_hides_it_and_restores_scoreboard(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime=ApplicationRuntime(folder)
            try:
                flow=BroadcastFlow(runtime,AsyncMock())
                await flow.begin({'event_id':'goal'})
                await flow.correct_event('goal')
                state=runtime.read_state()
                self.assertNotIn('pending_goal_celebration',state)
                self.assertEqual(state['broadcast_flow']['phase'],'IDLE')
                self.assertEqual(state['animation']['status'],'show')
                self.assertEqual(state['bottombar']['status'],'hide')
            finally: runtime.shutdown()
