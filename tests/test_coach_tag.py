import unittest
from unittest.mock import Mock
from manager_api.main import parse_import_content, build_player_import_template
from supabase_client import ScoreboardSupabaseClient as Client
from secretariat_core.services.match_context import _lineup_payload
import test_roster_bulk_import as roster_tests

class CoachTagTests(unittest.TestCase):
    def test_tag_in_both_importers(self):
        csv='Nombre;Posición;Entrenador;Dorsal\nAna;Defensa;Sí;7\nLuis;;Sí;\n'.encode()
        for roster in (False,True):
            rows=parse_import_content('a.csv',csv,roster=roster)[0]['rows']
            self.assertEqual(rows[0]['position'],'Defensa')
            self.assertEqual(Client._import_person_details(rows[0]),{'is_coach':True})
            self.assertTrue(Client._coach_only({**rows[1],**Client._import_person_details(rows[1])}))
    def test_player_coach_remains_one_membership_and_keeps_number(self):
        c=roster_tests.RosterBulkImportTests().client()
        row={'first_name':'Ana','last_name':'Paz','position':'Defensa','is_coach':'Sí','shirt_number':7}
        result=c.manager_import_roster('team','competition',[{'sheet':'CSV','rows':[row,row]}])
        self.assertEqual(result['totals']['created'],1);self.assertEqual(result['totals']['skipped'],1)
        c.manager_create_player.assert_called_once();c.manager_create_roster.assert_called_once()
        person=c.manager_create_player.call_args.args[0];member=c.manager_create_roster.call_args.args[0]
        self.assertEqual(person['position'],'defender');self.assertTrue(person['is_coach'])
        self.assertEqual(member['member_type'],'player');self.assertEqual(member['shirt_number'],7)
    def test_tag_existing_profile_without_duplicate(self):
        c=roster_tests.RosterBulkImportTests().client()
        c.manager_list_team_rosters.return_value=[{'player_id':'existing','shirt_number':7}]
        c.manager_update_player=Mock(return_value={'is_coach':True})
        row={'first_name':'Ana','last_name':'Paz','is_coach':'Sí'}
        result=c.manager_import_roster('team','competition',[{'sheet':'CSV','rows':[row]}])
        self.assertEqual(result['totals']['updated'],1)
        c.manager_create_player.assert_not_called();c.manager_create_roster.assert_not_called()
    def test_coach_only_has_no_shirt_or_captain(self):
        c=roster_tests.RosterBulkImportTests().client()
        row={'first_name':'Luis','is_coach':True,'shirt_number':7,'captain':True}
        c.manager_import_roster('team','competition',[{'rows':[row]}])
        member=c.manager_create_roster.call_args.args[0]
        self.assertEqual(member['member_type'],'coach');self.assertIsNone(member['shirt_number']);self.assertFalse(member['captain'])
    def test_lineup_includes_dual_person_once_each(self):
        row={'player_id':'p','member_type':'player','shirt_number':7,'player':{'first_name':'Ana','position':'defender','is_coach':True}}
        players,coaches=_lineup_payload([row],{},is_home=True)
        self.assertEqual(len(players),1);self.assertEqual(len(coaches),1);self.assertEqual(players[0]['number'],'7')
        row['member_type']='coach';row['player']['position']=None
        players,coaches=_lineup_payload([row],{},is_home=True)
        self.assertEqual(len(players),0);self.assertEqual(len(coaches),1)
    def test_invalid_tag_is_not_silently_true(self):
        with self.assertRaises(ValueError):Client._import_person_details({'is_coach':'maybe'})
