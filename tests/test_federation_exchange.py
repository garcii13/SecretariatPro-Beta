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
            p=self.payload
            if self.name=='players' and p.get('position') not in (None,'goalkeeper','defender','centre','forward','unknown'):raise ValueError('players_position_check')
            rows[p['id']]={**rows.get(p['id'],{}),**p};return SimpleNamespace(data=[rows[p['id']]])
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

class AutomaticCatalogTests(unittest.TestCase):
    setUp=FederationTests.setUp
    tearDown=FederationTests.tearDown
    exchange=FederationTests.exchange
    seed=FederationTests.seed
    client=FederationTests.client
    def worker(self,client,authorized=lambda:True):
        self.config['autoImport']=True
        os.environ['SP_FEDERATION_CONNECTIONS']=json.dumps([self.config])
        worker=object.__new__(fed.FederationWorker)
        worker.catalog_clients={('ws','one'):(client,authorized)};worker.errors={};worker.last_pull={};worker.contexts={}
        return worker
    def test_database_position_enum_and_structured_personal_fields(self):
        self.seed();client,db=self.client();e=self.exchange()
        data=catalog();p=data['entities'][2]['data']['players'][1]
        p.update(firstName='Ana',lastName='García López',birthDate='2001-03-04',nationality='España',isCoach=True)
        e.import_snapshot(data);e.close();fed.import_catalog(client,'one')
        row=db['players'][fed.local_id('ws','fed.test','player','h7')]
        self.assertEqual(row['position'],'centre');self.assertEqual(row['first_name'],'Ana');self.assertEqual(row['last_name'],'García López')
        self.assertEqual(row['birth_date'],'2001-03-04');self.assertEqual(row['nationality'],'España');self.assertTrue(row['is_coach'])
        for value in ['Centro','centre','center','midfielder','unknown','','something-else']:
            self.assertIn(fed.player_payload({'name':'Legacy alias','position':value})['position'],('goalkeeper','defender','centre','forward','unknown'))
    def test_bad_date_isolated_before_player_write_while_calendar_continues(self):
        self.seed();client,db=self.client();e=self.exchange();data=catalog();data['entities'][2]['data']['players'][0]['birthDate']='2001-02-30';e.import_snapshot(data);e.close()
        result=fed.import_catalog(client,'one')
        self.assertFalse(result['ok']);self.assertNotIn(fed.local_id('ws','fed.test','player','h9'),db['players'])
        self.assertEqual(len(db['players']),3);self.assertEqual(len(db['matches']),2)
        self.assertTrue(any(i['code']=='invalid_player' for i in result['issues']))
        self.assertTrue(any(i['kind']=='roster' for i in result['issues']))
        self.assertTrue(all(r['team_id']==fed.local_id('ws','fed.test','team','a') for r in db['rosters'].values()))
    def test_automatic_first_copy_retry_empty_feed_restart_and_live_score_no_reimport(self):
        self.seed();client,db=self.client();worker=self.worker(client)
        real_import=fed.import_catalog
        with patch.object(ExchangeClient,'pull',return_value=0),patch.object(fed,'import_catalog',side_effect=RuntimeError('temporary write failure')):
            worker.process('ws',{})
        self.assertIn(('ws','one'),worker.errors);self.assertEqual(db,{})
        worker.last_pull={}
        with patch.object(ExchangeClient,'pull',return_value=0),patch.object(fed,'import_catalog',wraps=real_import) as imported:
            worker.process('ws',{'online':{'match':{'id':'unlinked-local-game'}}})
            imported.assert_called_once();self.assertEqual(len(db['players']),4)
        # Applied digest persists across workers, and live facts do not rewrite rosters.
        worker=self.worker(client);e=self.exchange();row=catalog()['entities'][-2];row['revision']=2;row['data']['home']=99
        with e.db:e._store(row)
        e.close()
        with patch.object(ExchangeClient,'pull',return_value=0),patch.object(fed,'import_catalog') as imported:
            worker.process('ws',{});imported.assert_not_called()
        # A sporting profile edit does trigger a new automatic materialization.
        e=self.exchange();row=catalog()['entities'][2];row['revision']=2;row['data']['players'][0]['firstName']='Updated'
        with e.db:e._store(row)
        e.close();worker.last_pull={}
        with patch.object(ExchangeClient,'pull',return_value=0),patch.object(fed,'import_catalog',wraps=real_import) as imported:
            worker.process('ws',{});imported.assert_called_once()
        self.assertEqual(db['players'][fed.local_id('ws','fed.test','player','h9')]['first_name'],'Updated')
    def test_logged_out_or_switched_workspace_never_materializes(self):
        self.seed();client,db=self.client();worker=self.worker(client,lambda:False)
        with patch.object(ExchangeClient,'pull',return_value=0):worker.process('ws',{})
        self.assertEqual(db,{})
        worker.catalog_clients[('ws','one')]=(client,lambda:True);client._active_workspace_id.return_value='other';worker.last_pull={}
        with patch.object(ExchangeClient,'pull',return_value=0):worker.process('ws',{})
        self.assertEqual(db,{})
    def test_current_manager_registers_without_manual_import(self):
        self.seed();client,db=self.client();worker=self.worker(client);worker.catalog_clients={};worker.contexts={'ws':{'live':'preserved'}}
        with patch.object(fed,'_service',worker):fed.ensure_automatic(client,lambda:True)
        self.assertEqual(worker.catalog_clients[('ws','one')][0],client);self.assertEqual(worker.contexts['ws'],{'live':'preserved'})

    def test_partial_remote_copy_recovers_same_ids_without_manual_import(self):
        self.seed();client,db=self.client();worker=self.worker(client)
        original=client.client.table.side_effect
        failed=[False]
        def table(name):
            result=original(name);execute=result.execute
            def run():
                if name=='players' and len(db.get('players',{}))==1 and not failed[0]:
                    failed[0]=True;raise RuntimeError('interrupted after first player')
                return execute()
            result.execute=run
            return result
        client.client.table.side_effect=table
        with patch.object(ExchangeClient,'pull',return_value=0):worker.process('ws',{})
        self.assertEqual(len(db['players']),3);first_id=next(iter(db['players']))
        e=self.exchange();self.assertIsNone(e.applied('ws'));e.close();worker.last_pull={}
        with patch.object(ExchangeClient,'pull',return_value=0):worker.process('ws',{})
        self.assertEqual(len(db['players']),4);self.assertIn(first_id,db['players']);self.assertNotIn(('ws','one'),worker.errors)
        # Profile edits do not deactivate rosters or reset local captain flags.
        row=next(iter(db['rosters'].values()));row['captain']=True
        e=self.exchange();change=catalog()['entities'][2];change['revision']=2;change['data']['players'][0]['firstName']='Updated'
        with e.db:e._store(change)
        e.close();worker.last_pull={}
        with patch.object(ExchangeClient,'pull',return_value=0):worker.process('ws',{})
        self.assertTrue(row['active']);self.assertTrue(row['captain'])

    def test_optional_nulls_positions_and_numeric_shirts_are_normalized(self):
        self.seed();client,db=self.client();e=self.exchange();data=catalog();p=data['entities'][2]['data']['players'][0]
        p.update(number=' 09 ',position='  FORWARD  ',firstName=None,lastName=None,nationality=None,isCoach=None)
        e.import_snapshot(data);e.close();result=fed.import_catalog(client,'one');self.assertTrue(result['ok'])
        player=db['players'][fed.local_id('ws','fed.test','player','h9')];self.assertEqual(player['position'],'forward')
        self.assertTrue(any(r['shirt_number']==9 for r in db['rosters'].values()))
    def test_unknown_position_warns_without_blocking_or_inventing_position(self):
        self.seed();client,db=self.client();e=self.exchange();data=catalog();data['entities'][2]['data']['players'][0]['position']='unsupported-specialist'
        e.import_snapshot(data);e.close();result=fed.import_catalog(client,'one');self.assertTrue(result['ok'])
        self.assertTrue(any(i['level']=='warning' for i in result['issues']));self.assertEqual(db['players'][fed.local_id('ws','fed.test','player','h9')]['position'],'unknown')
    def test_rejected_player_preserves_valid_roster_and_recovers_on_source_correction(self):
        self.seed();client,db=self.client();fed.import_catalog(client,'one');before=copy.deepcopy(db['rosters']);e=self.exchange();row=catalog()['entities'][2]
        row['revision']=2;row['data']['players'][0]['birthDate']='invalid'
        with e.db:e._store(row)
        e.close();result=fed.import_catalog(client,'one');self.assertFalse(result['ok']);self.assertEqual(db['rosters'],before)
        e=self.exchange();self.assertGreater(e.catalog_health('ws')['catalogPending'],0);row['revision']=3;row['data']['players'][0]['birthDate']='2001-03-04'
        with e.db:e._store(row)
        e.close();result=fed.import_catalog(client,'one');self.assertTrue(result['ok']);e=self.exchange();self.assertEqual(e.catalog_health('ws')['catalogPending'],0);e.close()
    def test_failed_roster_retry_keeps_captain_even_after_deactivation(self):
        self.seed();client,db=self.client();fed.import_catalog(client,'one');captain=next(r for r in db['rosters'].values() if r['team_id']==fed.local_id('ws','fed.test','team','h'));captain['captain']=True
        e=self.exchange();row=catalog()['entities'][2];row['revision']=2;row['data']['players'][0]['number']=19
        with e.db:e._store(row)
        e.close();original=client.client.table.side_effect
        def table(name):
            result=original(name);execute=result.execute
            def run():
                if name=='rosters' and result.action=='upsert':raise RuntimeError('offline during roster update')
                return execute()
            result.execute=run;return result
        client.client.table.side_effect=table;result=fed.import_catalog(client,'one');self.assertFalse(result['ok']);self.assertFalse(captain['active'])
        client.client.table.side_effect=original;result=fed.import_catalog(client,'one');self.assertTrue(result['ok']);self.assertTrue(db['rosters'][captain['id']]['captain'])

    def test_unicode_data_and_known_position_aliases_do_not_depend_on_interface_language(self):
        for position,expected in [('målvakt','goalkeeper'),('brankář','goalkeeper'),('maalivahti','goalkeeper'),('Torhüter','goalkeeper'),('obránce','defender'),('puolustaja','defender'),('försvarare','defender'),('keskushyökkääjä','centre'),('Mittelstürmer','centre'),('útočník','forward'),('hyökkääjä','forward'),('Stürmer','forward')]:
            self.assertEqual(fed.player_payload({'name':'Åsa Černá','position':position})['position'],expected)
        self.seed();client,db=self.client();e=self.exchange();data=catalog();p=data['entities'][2]['data']['players'][0]
        p.update(name='Åsa Černá',firstName='Åsa',lastName='Černá',nationality='Sverige',birthDate='2001-03-04',position='målvakt')
        data['entities'][1]['data']['name']='Örnsköldsvik'
        e.import_snapshot(data);e.close();self.assertTrue(fed.import_catalog(client,'one')['ok'])
        player=db['players'][fed.local_id('ws','fed.test','player','h9')];self.assertEqual(player['last_name'],'Černá');self.assertEqual(player['nationality'],'Sverige')
        self.assertEqual(db['teams'][fed.local_id('ws','fed.test','team','h')]['name'],'Örnsköldsvik')

    def test_binding_cache_rebuild_recovers_only_exact_deterministic_ids(self):
        self.seed();client,db=self.client();fed.import_catalog(client,'one');before=set(db['rosters']);e=self.exchange()
        with e.db:
            e.db.execute('DELETE FROM bindings');e.db.execute('DELETE FROM materializations');e.db.execute('DELETE FROM catalog_sections')
        e.close();self.assertTrue(fed.import_catalog(client,'one')['ok']);self.assertEqual(set(db['rosters']),before)
        # An unrelated local row with an occupied shirt is never merged by name.
        e=self.exchange()
        with e.db:e.db.execute("DELETE FROM catalog_sections WHERE section LIKE 'roster:%'")
        e.close();team=fed.local_id('ws','fed.test','team','h');comp=fed.local_id('ws','fed.test','competition','c')
        db['rosters']['unrelated']={'id':'unrelated','team_id':team,'competition_id':comp,'shirt_number':9,'active':True}
        before=copy.deepcopy(db['rosters']);result=fed.import_catalog(client,'one');self.assertFalse(result['ok']);self.assertEqual(db['rosters'],before)

    def test_rich_player_fields_are_requested_only_when_provider_advertises_feature(self):
        e=self.exchange();data=catalog()
        def reply(method,path,*args):
            if path.endswith('/capabilities'):return {'schema':SCHEMA,'namespace':'fed.test','features':['player-details-v1']}
            self.assertIn('features=player-details-v1',path);return data
        e.request=Mock(side_effect=reply);e.bootstrap();self.assertEqual(len(e.snapshot('roster')),2);e.close()
        e=self.exchange();self.assertEqual(e.negotiated_features(),['player-details-v1']);e.close()
    def test_older_provider_works_without_feature_query_and_keeps_known_local_identity(self):
        e=self.exchange();seen=[]
        def reply(method,path,*args):
            seen.append(path)
            if path.endswith('/capabilities'):raise RuntimeError('not supported')
            return catalog()
        e.request=reply;e.bootstrap();self.assertFalse(any('features=' in path for path in seen));e.close()
        client,db=self.client();fed.import_catalog(client,'one');pid=fed.local_id('ws','fed.test','player','h9');db['players'][pid].update(first_name='Åsa',last_name='Černá',is_coach=True,birth_date='2001-03-04')
        self.assertTrue(fed.import_catalog(client,'one')['ok']);self.assertEqual(db['players'][pid]['last_name'],'Černá');self.assertTrue(db['players'][pid]['is_coach']);self.assertEqual(db['players'][pid]['birth_date'],'2001-03-04')
    def test_capability_upgrade_refreshes_snapshot_without_losing_outbox(self):
        self.seed();e=self.exchange();delivery=e.enqueue('m',{'clock':'01:00'})
        with e.db:e.db.execute('DELETE FROM capabilities_cache')
        def reply(method,path,*args):
            if path.endswith('/capabilities'):return {'schema':SCHEMA,'namespace':'fed.test','features':['player-details-v1']}
            self.assertIn('/snapshot?',path);return catalog()
        e.request=reply;e.pull();self.assertEqual(e.status()['pending'],1);self.assertEqual(e.db.execute('SELECT delivery FROM outbox').fetchone()[0],delivery);e.close()

    def test_malformed_optional_capabilities_fall_back_to_basic_contract(self):
        for advertised in ([],{'schema':SCHEMA,'namespace':'fed.test','features':None},{'schema':SCHEMA,'namespace':'fed.test','features':'player-details-v1'}):
            e=self.exchange()
            with e.db:e.db.execute('DELETE FROM capabilities_cache')
            e.request=lambda method,path: advertised if path.endswith('/capabilities') else catalog()
            self.assertGreater(e.bootstrap(),0);self.assertEqual(e.negotiated_features(),[]);e.close()
