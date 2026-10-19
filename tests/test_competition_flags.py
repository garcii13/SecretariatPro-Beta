import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from secretariat_api.runtime import ApplicationRuntime
from supabase_client import ScoreboardSupabaseClient


class Query:
    def __init__(self, rows, writes):
        self.rows, self.filters, self.writes = rows, {}, writes
        self.bounds = None

    def select(self, *args, **kwargs): return self
    def eq(self, key, value): self.filters[key] = value; return self
    def is_(self, key, value): self.filters[key] = None; return self
    def order(self, *args, **kwargs): return self
    def limit(self, *args): return self
    def range(self, start, end): self.bounds = (start, end); return self
    def insert(self, value): self.writes.append(value); return self
    def update(self, value): self.writes.append(value); return self
    def execute(self):
        rows = [row for row in self.rows if all(row.get(k) == v for k, v in self.filters.items())]
        if self.bounds:
            rows = rows[self.bounds[0]:self.bounds[1] + 1]
        return SimpleNamespace(data=rows)


class CompetitionFlagsTests(unittest.TestCase):
    def client(self):
        client = object.__new__(ScoreboardSupabaseClient)
        client.active_workspace = {'id': 'mine'}
        client._require_competition_manager = Mock()
        client._active_workspace_id = Mock(return_value='mine')
        self.rows = {
            'competitions': [{'id': 'cup', 'workspace_id': 'mine', 'is_international': True},
                             {'id': 'league', 'workspace_id': 'mine', 'is_international': False},
                             {'id': 'foreign', 'workspace_id': 'other', 'is_international': True}],
            'teams': [{'id': 'home', 'workspace_id': 'mine', 'flag_url': 'https://assets.test/es.svg', 'logo_url': 'crest'},
                      {'id': 'away', 'workspace_id': 'mine', 'flag_url': 'https://assets.test/fi.png'},
                      {'id': 'foreign', 'workspace_id': 'other', 'flag_url': 'https://other.test/flag.png'}],
            'sp_visual_themes': [],
        }
        self.writes = []
        client.client = SimpleNamespace(table=lambda table: Query(self.rows[table], self.writes))
        return client

    def test_international_without_a_theme_uses_team_flags_and_excludes_other_workspaces(self):
        client = self.client()
        theme = client.published_visual_theme('cup')
        identity = theme['competition_identity']
        self.assertTrue(identity['international'])
        self.assertEqual(set(identity['flags']), {'home', 'away'})
        with tempfile.TemporaryDirectory() as folder:
            runtime = ApplicationRuntime(folder)
            settings = runtime._apply_published_theme({}, theme)
            self.assertEqual(settings['appearance']['team_identity'], identity)
        self.assertEqual(self.rows['teams'][0]['logo_url'], 'crest')

    def test_competition_metadata_overrides_a_legacy_theme_and_resets_when_switching(self):
        client = self.client()
        self.rows['sp_visual_themes'] = [{'workspace_id': 'mine', 'competition_id': None, 'published': True,
            'config': {'appearance': {'team_identity': {'international': True, 'flags': {'old': 'https://old.test/flag'}},
                                     'scoreboard': {'background': '#123456'}}}}]
        with tempfile.TemporaryDirectory() as folder:
            runtime = ApplicationRuntime(folder)
            first = runtime._apply_published_theme({}, client.published_visual_theme('cup'))
            second = runtime._apply_published_theme(first, client.published_visual_theme('league'))
            self.assertEqual(second['appearance']['team_identity'], {'international': False, 'flags': {}})
            self.assertEqual(second['appearance']['scoreboard']['background'], '#123456')
            runtime.published_theme = client.published_visual_theme('league')
            forged = dict(first)
            self.assertFalse(runtime._enforce_locked_visual_theme(forged)['appearance']['team_identity']['international'])
        self.assertFalse(client.published_visual_theme()['competition_identity']['international'])

    def test_team_flag_changes_are_visible_without_republishing_a_theme(self):
        client = self.client()
        first = client.published_visual_theme('cup')
        self.rows['teams'][0]['flag_url'] = 'https://assets.test/new.svg'
        second = client.published_visual_theme('cup')
        self.assertNotEqual(first, second)
        self.assertEqual(second['competition_identity']['flags']['home'], 'https://assets.test/new.svg')

    def test_foreign_competition_cannot_load_flags(self):
        with self.assertRaises(ValueError): self.client().published_visual_theme('foreign')

    def test_flags_beyond_the_default_api_row_limit_are_not_lost(self):
        client = self.client()
        self.rows['teams'] = [{'id': str(n), 'workspace_id': 'mine', 'flag_url': f'https://assets.test/{n}.svg'} for n in range(1005)]
        flags = client.published_visual_theme('cup')['competition_identity']['flags']
        self.assertEqual(len(flags), 1005)
        self.assertEqual(flags['1004'], 'https://assets.test/1004.svg')

    def test_manager_writes_new_fields_separately_and_keeps_tenant_filters(self):
        client = self.client()
        client.manager_create_competition({'name': 'Cup', 'is_international': True, 'workspace_id': 'other'})
        self.assertEqual(self.writes[-1]['workspace_id'], 'mine')
        self.assertIs(self.writes[-1]['is_international'], True)
        client.manager_update_competition('cup', {'is_international': False})
        self.assertEqual(self.writes[-1], {'is_international': False})
        client.manager_create_team({'name': 'Spain', 'flag_url': 'https://assets.test/es.svg', 'logo_url': 'crest'})
        self.assertEqual(self.writes[-1]['logo_url'], 'crest')
        client.manager_update_team('home', {'flag_url': ''})
        self.assertEqual(self.writes[-1], {'flag_url': None})
        for value in ['false', None, 1]:
            with self.assertRaises(ValueError): client.manager_update_competition('cup', {'is_international': value})
        with self.assertRaises(ValueError): client.manager_update_team('home', {'flag_url': 'javascript:alert(1)'})


if __name__ == '__main__': unittest.main()
