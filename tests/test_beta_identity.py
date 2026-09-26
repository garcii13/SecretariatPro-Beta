import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from secretariat_core.visual_identity import normalize_elements, ELEMENTS
from secretariat_core.settings_store import normalize_settings
from secretariat_core.app_environment import data_directory
from secretariat_api.runtime import ApplicationRuntime
from supabase_client import ScoreboardSupabaseClient


class BetaIdentityTests(unittest.TestCase):
    def test_validation_handles_invalid_sizes_fonts_and_legacy_payloads(self):
        for raw in (None, [], 'bad', {}):
            self.assertEqual(len(normalize_elements(raw)), 10)
        for value, expected in [('bad', 1), (float('nan'), 1), (float('inf'), 1), (0, .5), (3, 1.5), (.8, .8)]:
            actual = normalize_elements({'scoreboard': {'scale': value, 'font': 'Arial; color:red'}})
            self.assertEqual(actual['scoreboard'], {'scale': expected, 'font': 'default'})
        self.assertEqual(normalize_settings({'appearance': None})['appearance']['elements']['scoreboard']['scale'], 1)

    def test_independent_settings_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime = ApplicationRuntime(folder)
            elements = {key: {'scale': .5 + i / 10, 'font': 'Georgia'} for i, key in enumerate(ELEMENTS)}
            runtime.published_theme = {'locked': False, 'config': {'appearance': {'elements': elements}}}
            settings = runtime.settings_store.load()
            settings['appearance']['elements']['scoreboard'] = {'scale': 1.5, 'font': 'Arial'}
            settings['appearance']['app_theme'] = 'light'
            runtime.save_current_settings(settings)
            result = runtime.read_state()['overlay_settings']['appearance']
            self.assertEqual(result['elements'], elements)
            self.assertEqual(result['app_theme'], 'light')
            self.assertTrue(runtime.safe_settings()['appearance_policy']['locked'])

    def test_competition_switch_resets_missing_values(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime = ApplicationRuntime(folder)
            client = Mock()
            client.published_visual_theme.return_value = {'config': {'appearance': {'elements': {'scoreboard': {'scale': .7, 'font': 'Verdana'}}}}}
            first = runtime._settings_with_published_theme(client, {}, 'first')
            client.published_visual_theme.return_value = {'config': {'appearance': {'panels': {'text': '#123456'}}}}
            second = runtime._settings_with_published_theme(client, first, 'second')
            self.assertEqual(second['appearance']['elements']['scoreboard'], {'scale': 1, 'font': 'default'})
            client.published_visual_theme.return_value = {}
            third = runtime._settings_with_published_theme(client, second, 'third')
            self.assertEqual(third['appearance']['panels']['text'], '#ffffff')

    def test_producer_cannot_override_unpublished_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            runtime = ApplicationRuntime(folder)
            settings = runtime.settings_store.load()
            settings['appearance']['elements']['scoreboard']['scale'] = .5
            runtime.save_current_settings(settings)
            self.assertEqual(runtime.settings_store.load()['appearance']['elements']['scoreboard']['scale'], 1)

    def test_single_plan_rejects_competition_scope(self):
        client = object.__new__(ScoreboardSupabaseClient)
        client.active_workspace = {'id': 'workspace', 'visual_identity_mode': 'single'}
        with self.assertRaises(PermissionError):
            client._validate_theme_scope('competition')

    def test_foreign_competition_rejected(self):
        client = object.__new__(ScoreboardSupabaseClient)
        client.active_workspace = {'id': 'workspace', 'visual_identity_mode': 'competition'}
        client.client = Mock()
        client.client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        with self.assertRaises(PermissionError):
            client._validate_theme_scope('foreign')

    def test_installed_data_lives_outside_bundle(self):
        with tempfile.TemporaryDirectory() as folder, patch('sys.frozen', True, create=True), patch('sys.platform', 'win32'), patch.dict('os.environ', {'LOCALAPPDATA': folder}):
            self.assertEqual(data_directory('/read-only/bundle'), Path(folder) / 'SecretariatPro')

    def test_installers_exclude_local_data(self):
        root = Path(__file__).resolve().parents[1]
        for spec in root.glob('*.spec'):
            source = spec.read_text()
            for private in ('app_settings.json', 'account_settings.json', 'subscription_access.json', 'data.json', 'ocr_config.json', 'ocr_training'):
                self.assertNotIn(private, source)
