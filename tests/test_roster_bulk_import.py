import unittest
from unittest.mock import Mock
from manager_api.main import parse_import_content
from supabase_client import ScoreboardSupabaseClient

class RosterBulkImportTests(unittest.TestCase):
    def client(self):
        c=object.__new__(ScoreboardSupabaseClient)
        c._require_competition_manager=Mock()
        c.manager_list_teams=Mock(return_value=[{'id':'team'}])
        c.manager_list_competitions=Mock(return_value=[{'id':'competition'}])
        c.manager_list_players=Mock(return_value=[{'id':'existing','first_name':'Ana','last_name':'Paz','display_name':'Ana Paz','position':None}])
        c.manager_list_team_rosters=Mock(return_value=[])
        c.manager_create_player=Mock(side_effect=lambda p:{**p,'id':'new'})
        c.manager_create_roster=Mock(return_value={'id':'membership'})
        return c
    def data(self,rows): return [{'sheet':'CSV','scope':'players','rows':rows}]
    def test_parser_retains_roster_fields_only_in_roster_mode(self):
        csv=b'Nombre;Apellidos;Dorsal;Capitan;Equipo\nAna;Paz;7;si;Ignored\n'
        row=parse_import_content('a.csv',csv,roster=True)[0]['rows'][0]
        self.assertEqual(row['shirt_number'],'7');self.assertEqual(row['captain'],'si');self.assertNotIn('team_name',row)
        self.assertNotIn('shirt_number',parse_import_content('a.csv',csv)[0]['rows'][0])
    def test_exact_profile_reused_and_repeated_row_skipped(self):
        c=self.client();r={'first_name':'Ana','last_name':'Paz','shirt_number':7}
        result=c.manager_import_roster('team','competition',self.data([r,r]))
        c.manager_create_player.assert_not_called();self.assertEqual(c.manager_create_roster.call_count,1)
        self.assertEqual(result['totals']['skipped'],1)
        self.assertEqual(c.manager_create_roster.call_args.args[0]['player_id'],'existing')
    def test_same_display_different_identity_is_not_overwritten(self):
        c=self.client();c.manager_import_roster('team','competition',self.data([{'first_name':'Ana','last_name':'Otra','display_name':'Ana Paz'}]))
        c.manager_create_player.assert_called_once()
    def test_existing_membership_is_skipped(self):
        c=self.client();c.manager_list_team_rosters.return_value=[{'player_id':'existing','shirt_number':9}]
        r=c.manager_import_roster('team','competition',self.data([{'first_name':'Ana','last_name':'Paz'}]))
        self.assertEqual(r['totals']['skipped'],1);c.manager_create_roster.assert_not_called()
    def test_shirt_conflict_before_profile_created(self):
        c=self.client();c.manager_list_team_rosters.return_value=[{'player_id':'other','shirt_number':7}]
        r=c.manager_import_roster('team','competition',self.data([{'first_name':'Nuevo','shirt_number':7}]))
        self.assertEqual(r['totals']['failed'],1);c.manager_create_player.assert_not_called()
    def test_foreign_target_rejected(self):
        c=self.client()
        with self.assertRaises(ValueError): c.manager_import_roster('foreign','competition',[])
        c.manager_create_player.assert_not_called()
    def test_retry_after_membership_failure_reuses_profile(self):
        c=self.client();c.manager_create_roster.side_effect=[ValueError('Temporary failure'),{'id':'ok'}]
        row={'first_name':'Nuevo'}
        r=c.manager_import_roster('team','competition',self.data([row,row]))
        self.assertEqual(r['totals']['failed'],1);self.assertEqual(r['totals']['created'],1)
        c.manager_create_player.assert_called_once()

class RosterImportAPITests(unittest.TestCase):
    def test_preview_and_commit_are_scoped(self):
        from fastapi.testclient import TestClient
        from unittest.mock import patch
        from manager_api import main
        client=Mock()
        client.manager_import_roster.return_value={'totals':{'created':1}}
        csv=b'Nombre;Apellidos;Dorsal\nAna;Paz;7\n'
        with patch.object(main.runtime,'require_write',return_value=client),patch.object(main.runtime,'require_connected',return_value=client):
            api=TestClient(main.app)
            url='/api/teams/team/rosters/competition/import/'
            preview=api.post(url+'analyze',files={'file':('people.csv',csv,'text/csv')})
            self.assertEqual(preview.status_code,200,preview.text)
            self.assertEqual(preview.json()['sheets'][0]['preview'][0]['shirt_number'],'7')
            client.manager_import_roster.assert_not_called()
            response=api.post(url+'commit',files={'file':('people.csv',csv,'text/csv')})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(client.manager_import_roster.call_args.args[:2],('team','competition'))
    def test_denied_cannot_import(self):
        from fastapi.testclient import TestClient
        from fastapi import HTTPException
        from unittest.mock import patch
        from manager_api import main
        with patch.object(main.runtime,'require_write',side_effect=HTTPException(403,'Forbidden')),patch.object(main.runtime,'require_connected') as connected:
            response=TestClient(main.app).post('/api/teams/team/rosters/competition/import/commit',files={'file':('people.csv',b'Nombre\nAna','text/csv')})
            self.assertEqual(response.status_code,403);connected.assert_not_called()

class RosterShirtTemplateTests(unittest.TestCase):
    def test_excel_template_roundtrip_with_shirt_and_captain(self):
        import io
        from openpyxl import load_workbook
        from manager_api.main import build_player_import_template, parse_import_content
        workbook=load_workbook(io.BytesIO(build_player_import_template(roster=True)))
        sheet=workbook.active
        headers=[c.value for c in sheet[1]]
        self.assertIn('Dorsal',headers);self.assertIn('Capitán',headers)
        row=[None]*len(headers)
        from manager_api.main import normalized_header
        for i,h in enumerate(headers):
            field=normalized_header(h)
            if field in ('first_name','name'): row[i]='Ana'
            elif field=='shirt_number': row[i]=27
            elif field=='captain': row[i]='Sí'
        sheet.append(row);out=io.BytesIO();workbook.save(out)
        parsed=parse_import_content('roster.xlsx',out.getvalue(),roster=True)[0]['rows'][0]
        self.assertEqual(parsed['shirt_number'],27)
        self.assertEqual(parsed['captain'],'Sí')
    def test_common_shirt_headers(self):
        from manager_api.main import parse_import_content
        for header in ['Dorsales','Nº dorsal','Número de camiseta','Shirt number','Jersey number']:
            with self.subTest(header=header):
                data=('Nombre;'+header+'\nAna;27\n').encode()
                self.assertEqual(parse_import_content('r.csv',data,roster=True)[0]['rows'][0]['shirt_number'],'27')
                self.assertNotIn('shirt_number',parse_import_content('r.csv',data)[0]['rows'][0])
