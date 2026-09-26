import io
import unittest
from datetime import datetime,time
from unittest.mock import Mock,patch
from openpyxl import Workbook
from manager_api.scoped_import import read_rows,preview,commit,schedule
from supabase_client import ScoreboardSupabaseClient

class FakeImportClient:
    _person_role=staticmethod(ScoreboardSupabaseClient._person_role)
    _import_position=staticmethod(ScoreboardSupabaseClient._import_position)
    _import_person_details=staticmethod(ScoreboardSupabaseClient._import_person_details)
    _normalise_shirt_number=staticmethod(ScoreboardSupabaseClient._normalise_shirt_number)
    _coach_only=staticmethod(ScoreboardSupabaseClient._coach_only)
    def __init__(self):
        self.teams=[{'id':'t1','name':'Equipo Uno','short_name':'UNO'},{'id':'t2','name':'Equipo Dos','short_name':'DOS'}]
        self.groups=[];self.matches=[];self.roster_calls=[]
    def manager_list_competitions(self):return [{'id':'c1','name':'Liga','season_id':'s1'},{'id':'c2','name':'Otra liga','season_id':'s2'}]
    def manager_list_seasons(self):return [{'id':'s1','name':'2026/27'},{'id':'s2','name':'2025/26'}]
    def manager_list_teams(self):return self.teams
    def manager_list_roster_groups(self):return self.groups
    def manager_list_team_rosters(self,*args):return []
    def manager_import_roster(self,*args):
        self.roster_calls.append(args)
        return {'totals':{'created':1,'skipped':0,'updated':0,'failed':0},'errors':[]}
    def manager_import_fixture(self,payload):
        if payload in self.matches:return {'created':False}
        self.matches.append(payload);return {'created':True}
    def manager_create_team(self,payload):
        team={'id':'t'+str(len(self.teams)+1),**payload};self.teams.append(team);return team
    def manager_create_roster_group(self,team_id,competition_id):
        row={'id':'g'+str(len(self.groups)+1),'team_id':team_id,'competition_id':competition_id};self.groups.append(row);return row

class ScopedImportTests(unittest.TestCase):
    def people(self,team='UNO'):
        return read_rows('p.csv',f'Nombre;Equipo;Dorsal;Entrenador\nAna;{team};7;Sí\n'.encode(),'people')
    def matches(self,home='UNO'):
        return read_rows('m.csv',f'Fecha;Hora;Instalación;Local;Visitante\n25/09/2026;;Pista;{home};DOS\n'.encode(),'matches')
    def test_people_preserves_team_shirt_and_tag(self):
        row=self.people()[0]['data'];self.assertEqual(row['team_name'],'UNO');self.assertEqual(row['shirt_number'],'7');self.assertEqual(row['is_coach'],'Sí')
    def test_requires_matching_season(self):
        with self.assertRaises(ValueError):preview(FakeImportClient(),'people',self.people(),'c1','s2','Europe/Madrid')
    def test_unknown_team_and_empty_roster_are_actionable_without_writes(self):
        c=FakeImportClient();result=preview(c,'people',self.people('Missing'),'c1','s1','Europe/Madrid')
        self.assertEqual(result['missing_teams'],['Missing']);self.assertFalse(result['ready'])
        result=preview(c,'people',self.people(),'c1','s1','Europe/Madrid')
        self.assertEqual(result['missing_rosters'],[{'team_id':'t1','name':'Equipo Uno'}]);self.assertFalse(c.roster_calls)
        c.manager_create_roster_group('t1','c1')
        result=commit(c,'people',self.people(),'c1','s1','Europe/Madrid')
        self.assertEqual(result['totals']['created'],1);self.assertEqual(c.roster_calls[0][:2],('t1','c1'))
    def test_fixtures_unknown_team_blocks_all_writes(self):
        c=FakeImportClient();result=commit(c,'matches',self.matches('Missing'),'c1','s1','Europe/Madrid')
        self.assertTrue(result['blocked']);self.assertFalse(c.matches)
    def test_no_time_and_reimport(self):
        c=FakeImportClient();rows=self.matches()
        self.assertEqual(commit(c,'matches',rows,'c1','s1','Europe/Madrid')['totals']['created'],1)
        self.assertFalse(c.matches[0]['time_confirmed']);self.assertEqual(c.matches[0]['scheduled_date'],'2026-09-25')
        self.assertEqual(commit(c,'matches',rows,'c1','s1','Europe/Madrid')['totals']['skipped'],1)
    def test_excel_dates_and_times(self):
        book=Workbook();book.active.append(['Fecha','Hora','Local','Visitante']);book.active.append([datetime(2026,9,25),time(19,30),'UNO','DOS'])
        out=io.BytesIO();book.save(out);row=read_rows('m.xlsx',out.getvalue(),'matches')[0]['data']
        self.assertEqual(schedule(row,'Europe/Madrid'),('2026-09-25T17:30:00+00:00',True))
    def test_invalid_date_time_and_same_team(self):
        for row in [{'date':'31/02/2026'},{'date':'25/09/2026','time':'25:30'},{'date':'29/03/2026','time':'02:30'}]:
            with self.assertRaises(ValueError):schedule(row,'Europe/Madrid')
        c=FakeImportClient();self.assertFalse(preview(c,'matches',self.matches('DOS'),'c1','s1','Europe/Madrid')['ready'])
    def test_ambiguous_team_is_rejected(self):
        c=FakeImportClient();c.teams.append({'id':'t3','name':'UNO'})
        self.assertIn('ambiguo',preview(c,'people',self.people(),'c1','s1','Europe/Madrid')['errors'][0])
    def test_scoped_api_preview_commit_and_permissions(self):
        from manager_api import main
        from fastapi.testclient import TestClient
        from fastapi import HTTPException
        c=FakeImportClient();api=TestClient(main.app);url='/api/import/scoped/matches/'
        content=b'Fecha;Local;Visitante\n25/09/2026;UNO;DOS\n'
        with patch.object(main.runtime,'require_write',return_value=c),patch.object(main.runtime,'require_connected',return_value=c):
            response=api.post(url+'analyze?competition_id=c1&season_id=s1',files={'file':('m.csv',content)})
            self.assertEqual(response.status_code,200,response.text);self.assertTrue(response.json()['ready']);self.assertFalse(c.matches)
            response=api.post(url+'commit?competition_id=c1&season_id=s1',files={'file':('m.csv',content)})
            self.assertEqual(response.json()['totals']['created'],1)
        with patch.object(main.runtime,'require_write',side_effect=HTTPException(403,'Forbidden')):
            self.assertEqual(api.post(url+'commit?competition_id=c1&season_id=s1',files={'file':('m.csv',content)}).status_code,403)
