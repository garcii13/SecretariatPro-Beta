import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from secretariat_core.exchange.client import ExchangeClient, SCHEMA, signed_headers
from secretariat_core.exchange import federation as fed


def catalog(namespace='fed.test'):
    def entity(kind,ident,data):return {'kind':kind,'id':ident,'revision':1,'data':{'id':ident,**data}}
    entities=[entity('competition','c',{'name':'Federation Cup','season':'2026/27','category':'Open','pointsWin':2,'pointsDraw':1,'pointsLoss':0})]
    for tid in ('h','a'):
        entities.append(entity('team',tid,{'name':tid,'shortName':tid,'logo':''}))
        entities.append(entity('roster','r'+tid,{'teamId':tid,'season':'2026/27','archived':False,'players':[{'id':tid+'9','name':'Same name','number':9,'position':'Delantera'},{'id':tid+'7','name':tid+' assistant','number':7,'position':'Centro'}]}))
    lineup=[{'teamId':t,'playerId':t+str(n),'name':'Same name','number':n,'position':''} for t in ('h','a') for n in (9,7)]
    for mid,status in [('m','official'),('other','provisional')]:
        entities.append(entity('match',mid,{'competitionId':'c','season':'2026/27','homeTeamId':'h','awayTeamId':'a','startsAt':'2026-11-04T18:00:00Z','venue':'Test','matchStatus':'finished','home':1,'away':0,'clock':'60:00','period':'3','reviewStatus':status,'captureAllowed':False,'lineup':lineup,'events':[{'id':'g','teamId':'h','type':'goal','seconds':62,'playerId':'h9','assistantId':'h7'}],'keepers':[]}))
    return {'schema':SCHEMA,'namespace':namespace,'competitionId':'c','entities':entities,'nextCursor':'10'}

class Table:
    def __init__(self,db,name):self.db=db;self.name=name;self.filters={};self.action='select';self.payload={}
    def upsert(self,p):self.action='upsert';self.payload=copy.deepcopy(p);return self
    def insert(self,p):return self.upsert({'id':'generated',**p})
    def select(self,*a):return self
    def update(self,p):self.action='update';self.payload=p;return self
    def eq(self,k,v):self.filters[k]=v;return self
    def execute(self):
        rows=self.db.setdefault(self.name,{})
        if self.action=='upsert':
            p=self.payload;rows[p['id']]={**rows.get(p['id'],{}),**p};return SimpleNamespace(data=[rows[p['id']]])
        selected=[r for r in rows.values() if all(r.get(k)==v for k,v in self.filters.items())]
        if self.action=='update':
            for row in selected:row.update(self.payload)
        return SimpleNamespace(data=copy.deepcopy(selected))

class FederationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'cache.sqlite'
        self.config={'id':'one','url':'http://127.0.0.1:4321','clientId':'producer','secretEnv':'EXCHANGE_TEST_SECRET','namespace':'fed.test','competitionId':'c','workspaceId':'ws','modules':['catalog','captures','statistics'],'enabled':True}
        self.env=patch.dict(os.environ,{'SP_EXCHANGE_CACHE':str(self.path),'SP_FEDERATION_CONNECTIONS':json.dumps([self.config]),'EXCHANGE_TEST_SECRET':'test-secret-which-is-at-least-32-chars'});self.env.start()
    def tearDown(self):fed.stop_worker();self.env.stop();self.tmp.cleanup()
    def exchange(self,namespace='fed.test'):
        return ExchangeClient('http://127.0.0.1:4321','producer',os.environ['EXCHANGE_TEST_SECRET'],namespace,'c',self.path)
    def seed(self):
        e=self.exchange();e.request=Mock(return_value=catalog());e.bootstrap();e.close()
    def client(self):
        db={};client=Mock();client._active_workspace_id.return_value='ws';client.client.table.side_effect=lambda name:Table(db,name)
        client.manager_list_team_rosters.side_effect=lambda team,comp:[r for r in db.get('rosters',{}).values() if r['team_id']==team and r['competition_id']==comp and r['active']]
        return client,db
    def test_no_configuration_leaves_baseline_independent(self):
        with patch.dict(os.environ,{'SP_FEDERATION_CONNECTIONS':'[]'}),patch.object(fed,'FederationWorker') as worker:
            fed.observe_runtime(SimpleNamespace(active_workspace={'id':'ws'}),{'online':{}})
            worker.assert_not_called()
    def test_namespace_scope_and_private_fields_rejected(self):
        e=self.exchange();e.request=Mock(return_value=catalog('other.fed'))
        with self.assertRaises(ValueError):e.bootstrap()
        data=catalog();data['entities'][0]['data']['email']='private'
        e.request.return_value=data
        with self.assertRaises(ValueError):e.bootstrap()
        self.assertEqual(e.snapshot('team'),[]);e.close()
    def test_two_federations_can_use_same_ids_without_collision(self):
        a=self.exchange();a.request=Mock(return_value=catalog());a.bootstrap()
        b=self.exchange('other.fed');b.request=Mock(return_value=catalog('other.fed'));b.bootstrap()
        a.bind('player','h9','local-a');b.bind('player','h9','local-b')
        self.assertEqual(a.mapped('player','h9'),'local-a');self.assertEqual(b.mapped('player','h9'),'local-b');a.close();b.close()
    def test_delivery_survives_restart_review_does_not_close_desk(self):
        e=self.exchange();data={'clock':'01:02'};delivery=e.enqueue('m',data)
        self.assertIsNone(e.enqueue('m',data));e.request=Mock(side_effect=RuntimeError('offline'))
        with self.assertRaises(RuntimeError):e.flush()
        e.close();e=self.exchange();e.request=Mock(return_value={'ok':True,'accepted':False,'reason':'review_pending','deskMayContinue':True})
        e.flush();self.assertEqual(e.request.call_args.args[3],delivery)
        envelope=e.request.call_args.args[2];self.assertEqual(envelope['specversion'],'1.0');self.assertEqual(envelope['data']['revision'],1)
        self.assertEqual(e.status()['pending'],0)
        self.assertIsNotNone(e.enqueue('m',{'clock':'01:03'}));self.assertEqual(e.status()['pending'],1)
        dump='\n'.join(e.db.iterdump());self.assertNotIn(os.environ['EXCHANGE_TEST_SECRET'],dump);e.close()
    def test_snapshot_cursor_recovery_and_revision_corrections(self):
        e=self.exchange();data=catalog();e.request=Mock(return_value=data);e.bootstrap()
        row=copy.deepcopy(data['entities'][-2]);row['revision']=2;row['cursor']='11';row['data']['events']=[];row['data']['home']=0
        e.request.return_value={'schema':SCHEMA,'namespace':'fed.test','competitionId':'c','changes':[row],'nextCursor':'11','hasMore':False}
        self.assertEqual(e.pull(),1);self.assertEqual(next(r for r in e.snapshot('match') if r['id']=='m')['events'],[])
        self.assertIn('after=10',e.request.call_args.args[1]);e.close()
    def test_cache_rebuild_restores_producer_revision_checkpoint(self):
        e=self.exchange();data=catalog();data['captureCheckpoints']=[{'matchId':'m','revision':100}]
        e.import_snapshot(data);e.enqueue('m',{'clock':'02:00'})
        body=json.loads(e.db.execute('SELECT body FROM outbox').fetchone()[0])
        self.assertEqual(body['data']['revision'],101);e.close()
    def test_federation_catalog_identity_first_no_name_merge_and_no_event_import(self):
        self.seed();client,db=self.client();result=fed.import_catalog(client,'one')
        self.assertTrue(result['ok']);self.assertEqual(len(db['players']),4);self.assertNotIn('match_events',db)
        ids=set(db['players']);self.assertNotEqual(fed.local_id('ws','fed.test','player','h9'),fed.local_id('ws','fed.test','player','a9'))
        team=next(iter(db['teams'].values()));team['primary_color']='#123456'
        fed.import_catalog(client,'one');self.assertEqual(ids,set(db['players']));self.assertEqual(team['primary_color'],'#123456')
        match=next(iter(db['matches'].values()));self.assertEqual(match['home_score'],0)
    def test_connected_identity_readonly_disconnected_copy_usable(self):
        self.seed();client,db=self.client();fed.import_catalog(client,'one')
        pid=fed.local_id('ws','fed.test','player','h9')
        with self.assertRaises(PermissionError):fed.assert_local_write(client,'player',pid)
        with patch.dict(os.environ,{'SP_FEDERATION_CONNECTIONS':'[]'}):fed.assert_local_write(client,'player',pid)
        fed.assert_local_write(client,'player','unrelated-local')
    def live(self,e):
        def mapped(k,i):return e.mapped(k,i)
        rosters={side:[{'player_id':mapped('player',tid+str(n)),'shirt_number':n,'player':{'id':mapped('player',tid+str(n)),'display_name':tid+str(n)}} for n in (9,7)] for side,tid in [('team1','h'),('team2','a')]}
        return {'online':{'match':{'id':mapped('match','m'),'home_team':{'id':mapped('team','h')},'away_team':{'id':mapped('team','a')},'status':'scheduled'},'rosters':rosters,'attendance':{k:[r['player_id'] for r in v] for k,v in rosters.items()},'events':[{'id':'goal','event_type':'goal','team_id':mapped('team','h'),'player_id':mapped('player','h9'),'match_time':'01:02','created_at':'2026-11-04T18:01:02Z'},{'id':'assist','event_type':'assist','team_id':mapped('team','h'),'player_id':mapped('player','h7'),'related_event_id':'goal'}]},'scores':{'team1_score':1,'team2_score':0,'time':'01:02'},'state':{'match':{'period':3}}}
    def test_live_goal_before_close_attendance_assist_unknown_historic_period(self):
        self.seed();client,db=self.client();fed.import_catalog(client,'one');e=self.exchange();s=self.live(e)
        mid,data=fed.convert_capture(s,e);self.assertEqual(mid,'m');self.assertEqual(data['matchStatus'],'live');self.assertEqual(data['report']['events'][0]['assistantId'],'h7')
        self.assertEqual(data['report']['events'][0]['period'],'');self.assertEqual(data['report']['events'][0]['timeBasis'],'source_clock')
        s['online']['events']=[];self.assertEqual(fed.convert_capture(s,e)[1]['report']['events'],[]);e.close()
    def test_official_projection_excludes_provisional_and_replaces_current_match(self):
        self.seed();client,db=self.client();fed.import_catalog(client,'one');comp=fed.local_id('ws','fed.test','competition','c')
        p=fed.statistics(client,comp);self.assertEqual(sum(r['goals'] for r in p['players']),1)
        e=self.exchange();live=self.live(e);p=fed.statistics(client,comp,live);e.close()
        self.assertEqual(sum(r['goals'] for r in p['players']),1);self.assertTrue(p['provisionalIncluded']);self.assertEqual(p['standings'][0]['played'],0)
    def test_broadcast_match_allows_missing_or_blank_operator(self):
        from supabase_client import ScoreboardSupabaseClient
        c=object.__new__(ScoreboardSupabaseClient);c._require_competition_manager=Mock();c._active_workspace_id=Mock(return_value='ws')
        db={};c.client=Mock();c.client.table.side_effect=lambda name:Table(db,name)
        for assigned in [None,'','   ']:
            result=c.manager_create_match({'id':'ignored','competition_id':'c','home_team_id':'h','away_team_id':'a','match_date':'2026-11-04T18:00:00Z','assigned_to':assigned,'broadcast_enabled':True})
            self.assertIsNone(result['assigned_to']);self.assertTrue(result['broadcast_enabled'])
        c.manager_update_match('generated',{'assigned_to':'','broadcast_enabled':True})
