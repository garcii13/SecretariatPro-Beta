import io, unittest
from datetime import datetime
from unittest.mock import Mock
from openpyxl import load_workbook
from manager_api.main import parse_import_content, build_player_import_template
from supabase_client import ScoreboardSupabaseClient as Client

class PersonalDetailsTests(unittest.TestCase):
    def test_both_csv_importers(self):
        content='Nombre;Fecha de nacimiento;Nacionalidad\nAna;04/05/2000;España\n'.encode()
        for roster in (False,True):
            row=parse_import_content('a.csv',content,roster=roster)[0]['rows'][0]
            self.assertEqual(Client._import_person_details(row),{'birth_date':'2000-05-04','nationality':'España'})
    def test_both_excel_templates_and_date_cells(self):
        for roster in (False,True):
            wb=load_workbook(io.BytesIO(build_player_import_template(roster=roster)));sheet=wb.active
            headers=[c.value for c in sheet[1]]
            self.assertIn('nationality',headers);self.assertIn('birth_date',headers)
            values={'first_name':'Ana','birth_date':datetime(2000,5,4),'nationality':'ES'}
            sheet.append([values.get(h) for h in headers]);out=io.BytesIO();wb.save(out)
            row=parse_import_content('a.xlsx',out.getvalue(),roster=roster)[0]['rows'][0]
            self.assertEqual(Client._import_person_details(row)['birth_date'],'2000-05-04')
    def test_invalid_dates_are_rejected(self):
        for value in ['31/02/2000','01/01/2999','04/05/00',123]:
            with self.subTest(value=value),self.assertRaises(ValueError):Client._import_person_details({'birth_date':value})
        self.assertEqual(Client._import_person_details({}),{})
    def test_general_import_exact_identity_includes_birth_and_nationality(self):
        c=object.__new__(Client);c._require_competition_manager=Mock();c._active_workspace_id=Mock(return_value='workspace')
        for name in ['seasons','competitions','teams','members','matches','themes']:
            setattr(c,'manager_list_'+name,Mock(return_value=[]))
        person={'id':'old','first_name':'Ana','last_name':None,'display_name':'Ana','position':None,'birth_date':'2000-05-04','nationality':'ES'}
        c.manager_list_players=Mock(return_value=[person]);c.manager_create_player=Mock(side_effect=lambda p:{**p,'id':'new'})
        c.manager_update_player=Mock()
        query=Mock();query.select.return_value=query;query.eq.return_value=query;query.execute.return_value.data=[]
        c.client=Mock();c.client.table.return_value=query
        rows=[{'first_name':'Ana','birth_date':'04/05/2000','nationality':'ES'}, {'first_name':'Ana','birth_date':'05/05/2000','nationality':'ES'}]
        result=c.manager_import_rows([{'sheet':'CSV','scope':'players','rows':rows}])
        self.assertEqual(result['totals']['skipped'],1);self.assertEqual(result['totals']['created'],1)
        c.manager_update_player.assert_not_called()
