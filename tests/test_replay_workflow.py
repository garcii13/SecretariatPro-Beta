import asyncio
import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from secretariat_core.ocr_store import ScoreFileStore
from secretariat_core.services.broadcast_flow import BroadcastFlow
from secretariat_core.services.overlay import panel_visible
from secretariat_core.services.replay_library import ReplayLibrary
from secretariat_core.settings_store import normalize_settings


class GraphicScoreTests(unittest.TestCase):
    def test_goal_does_not_change_ocr_scoreboard_and_catchup_does_not_double_count(self):
        with tempfile.TemporaryDirectory() as d:
            store = ScoreFileStore(d)
            store.write_external({'team1_score': 2, 'team2_score': 1, 'time': '12:34'})
            self.assertEqual(store.confirm_goal('team1_score', 2), 3)
            self.assertEqual(store.read('team1_score'), '2')
            store.write_external({'team1_score': 2, 'time': '12:35'})
            self.assertEqual(store.reconciliation()['team1_score']['internal'], 3)
            self.assertTrue(store.reconciliation()['team1_score']['pending'])
            self.assertEqual(store.read('time'), '12:35')
            store.write_external({'team1_score': 3})
            self.assertFalse(store.reconciliation()['team1_score']['pending'])
            self.assertEqual(store.reconciliation()['team1_score']['internal'], 3)
            self.assertEqual(store.read('team1_score'), '3')
            store.write_external({'team1_score': 2})
            self.assertEqual(store.read('team1_score'), '2')  # explicit user requirement: scoreboard always OCR
            self.assertEqual(store.reconciliation()['team1_score']['internal'], 3)

    def test_multiple_goals_ocr_first_manual_correction_and_restart(self):
        with tempfile.TemporaryDirectory() as d:
            store = ScoreFileStore(d)
            store.write_external({'team1_score': 2})
            self.assertEqual(store.confirm_goal('team1_score', 2), 3)
            self.assertEqual(store.confirm_goal('team1_score', 3), 4)
            self.assertEqual(ScoreFileStore(d).reconciliation()['team1_score']['internal'], 4)
            store.write_external({'team1_score': 5})
            self.assertEqual(store.confirm_goal('team1_score', 4), 5)
            store.correct_score('team1_score', 1)
            store.write_external({'team1_score': 1})
            self.assertEqual(store.reconciliation()['team1_score']['internal'], 1)
            store.reset_reconciliation()
            self.assertEqual(store.reconciliation(), {})


class FakeRuntime:
    def __init__(self):
        self.state = {'match': {'period': 2}, 'animation': {'status': 'show'}, 'bottombar': {}}
        self.plugin = {'available': True, 'playing': True}
        self.replay_plugin = SimpleNamespace(status=lambda: dict(self.plugin))
    def mutate_state(self, mutation):
        mutation(self.state)
    def read_state(self):
        return copy.deepcopy(self.state)
    def safe_settings(self):
        return {'appearance': {'goal_celebration': {'delay_seconds': .02, 'duration_seconds': .02}}}


class BroadcastTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = FakeRuntime()
        self.frames = []
        async def broadcast():
            self.frames.append(copy.deepcopy(self.runtime.state))
        self.flow = BroadcastFlow(self.runtime, broadcast)
    async def asyncTearDown(self):
        self.flow.cancel()
    async def until(self, phase):
        async def poll():
            while self.runtime.state.get('broadcast_flow', {}).get('phase') != phase:
                await asyncio.sleep(.005)
        await asyncio.wait_for(poll(), 2)
    async def test_goal_waits_for_real_return_then_bottom_then_scoreboard(self):
        await self.flow.begin({'scorer': 'Garcia'})
        await self.flow.playing(goal=True)
        await asyncio.sleep(.04)
        self.assertFalse(panel_visible(self.runtime.state, 'scoreboard'))
        self.assertFalse(panel_visible(self.runtime.state, 'bottom_bar'))
        self.runtime.state['match']['period'] = 3
        self.runtime.plugin['playing'] = False
        await self.until('IDLE')
        phases = [f['broadcast_flow']['phase'] for f in self.frames]
        self.assertEqual(phases, ['BUILDING','REPLAY','LIVE','GOAL_BOTTOM','IDLE'])
        bottom = self.frames[-2]
        self.assertFalse(panel_visible(bottom,'scoreboard'))
        self.assertTrue(panel_visible(bottom,'bottom_bar'))
        self.assertEqual(bottom['bottombar']['scorer'],'Garcia')
        self.assertTrue(panel_visible(self.frames[-1],'scoreboard'))
        self.assertFalse(panel_visible(self.frames[-1],'bottom_bar'))
        self.assertEqual(self.runtime.state['match']['period'],3)
    async def test_no_replay_delay_and_library_replay_has_no_goal_bottom(self):
        await self.flow.begin({'scorer':'Garcia'})
        self.runtime.plugin['playing'] = False
        await self.flow.without_replay()
        await self.until('IDLE')
        self.assertIn('GOAL_DELAY',[f['broadcast_flow']['phase'] for f in self.frames])
        self.frames.clear()
        await self.flow.begin()
        self.runtime.plugin['playing'] = False
        await self.flow.playing(goal=False)
        await self.until('IDLE')
        self.assertNotIn('GOAL_BOTTOM',[f['broadcast_flow']['phase'] for f in self.frames])
    async def test_lost_connection_never_presents_bottom_until_confirmed_live(self):
        await self.flow.begin({'scorer':'Garcia'})
        self.runtime.plugin['available'] = False
        await self.flow.playing(goal=True)
        await self.until('REPLAY_CONNECTION_LOST')
        self.assertFalse(panel_visible(self.runtime.state,'bottom_bar'))
        self.runtime.plugin.update(available=True,playing=False)
        await self.until('IDLE')
    async def test_new_flow_cancels_previous_delay(self):
        await self.flow.begin({'scorer':'old'})
        await self.flow.without_replay()
        await self.flow.begin({'scorer':'new'})
        await asyncio.sleep(.05)
        self.assertEqual(self.runtime.state['broadcast_flow']['phase'],'BUILDING')
        self.assertFalse(panel_visible(self.runtime.state,'bottom_bar'))


class ReplayMetadataTests(unittest.TestCase):
    def test_all_four_speeds_and_personal_templates_survive_normalization(self):
        with tempfile.TemporaryDirectory() as d:
            library=ReplayLibrary(d)
            clip=library.create_marker(match_id='m',label='Parada',period=2,match_time='12:34')
            segments=[{'camera':1,'duration_seconds':3,'speed_percent':speed} for speed in (100,75,50,25)]
            saved=library.set_composition(clip['id'],segments)
            self.assertEqual(saved['composition'],segments)
            self.assertEqual(saved['period'],2)
        template={'id':'personal','name':'Normal','segments':segments,'default':True}
        self.assertEqual(normalize_settings({'replay_templates':[template]})['replay_templates'],[template])
