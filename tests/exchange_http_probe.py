"""Real HTTP contract check. Temporary AEUF DB + synthetic Supabase transport only."""
import json
import os
import sys
import urllib.request
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from secretariat_core.exchange.client import ExchangeClient
from secretariat_core.exchange import federation as fed
from secretariat_core.exchange import connections as wizard
from tests.test_federation_exchange import FederationTests
base=os.environ['EXCHANGE_HTTP_URL'];secret=os.environ['EXCHANGE_HTTP_SECRET'];checks=0
config={'id':'test','url':base,'namespace':'fed.test','clientId':'producer','secretEnv':'EXCHANGE_HTTP_SECRET','competitionId':'liga-oro','workspaceId':'ws','enabled':True,'modules':['catalog','captures','statistics']}
os.environ['SP_FEDERATION_CONNECTIONS']=json.dumps([config])
def check(value):
 global checks
 assert value
 checks+=1

def api(path,data=None,method=None,session=None):
 raw=json.dumps(data).encode() if data is not None else None
 headers={'Origin':base,'Content-Type':'application/json','Cookie':'aeuf_session='+(session or os.environ['EXCHANGE_HTTP_SESSION'])}
 with urllib.request.urlopen(urllib.request.Request(base+path,data=raw,headers=headers,method=method or ('POST' if raw else 'GET'))) as r:return json.load(r)

e=ExchangeClient(base,'producer',secret,'fed.test','liga-oro',os.environ['SP_EXCHANGE_CACHE'])
try:
 check(e.bootstrap()>0);check(len(e.snapshot('roster'))>=2)
 fixture=FederationTests();client,db=fixture.client();result=fed.import_catalog(client,'test')
 check(result['ok']);check('match_events' not in db)
 game=next(m for m in e.snapshot('match') if m['id']=='exchange-match')
 local=lambda kind,ident:e.mapped(kind,ident)
 rosters={}
 for key,tid in [('team1','exchange-h'),('team2','exchange-a')]:
  rosters[key]=[{**r,'player':db['players'][r['player_id']]} for r in db['rosters'].values() if r['team_id']==local('team',tid) and r['active']]
 scorer=next(r for r in rosters['team1'] if r['shirt_number']==9)['player_id'];assistant=next(r for r in rosters['team1'] if r['shirt_number']==7)['player_id']
 snap={'online':{'match':{'id':local('match','exchange-match'),'home_team':{'id':local('team','exchange-h')},'away_team':{'id':local('team','exchange-a')},'status':'scheduled'},'rosters':rosters,'attendance':{k:[r['player_id'] for r in rows] for k,rows in rosters.items()},'events':[{'id':'live-goal','event_type':'goal','team_id':local('team','exchange-h'),'player_id':scorer,'match_time':'02:00'},{'id':'live-assist','event_type':'assist','team_id':local('team','exchange-h'),'player_id':assistant,'related_event_id':'live-goal'}]},'scores':{'team1_score':1,'team2_score':0,'time':'02:00'},'state':{'match':{'period':1}}}
 mid,capture=fed.convert_capture(snap,e);check(capture['matchStatus']=='live')
 delivery=e.enqueue(mid,capture);check(delivery is not None)
 receipts=e.flush();check(receipts[0]['accepted'])
 e.pull();stored=next(m for m in e.snapshot('match') if m['id']==mid);check(len(stored['events'])==1);check(stored['reviewStatus']=='provisional');check(stored['events'][0]['assistantId']=='qa-assist')
 # A correction replaces its earlier revision. No second goal is inserted.
 capture['report']['events'][0]['seconds']=125;e.enqueue(mid,capture);check(e.flush()[0]['accepted']);e.pull()
 check(next(m for m in e.snapshot('match') if m['id']==mid)['events'][0]['seconds']==125)
 report=api('/api/match-report?edit=1&match='+mid)
 api('/api/match-report/confirm',{'matchId':mid,'version':report['version'],'correctFinalScore':True});check(True)
 capture['clock']='02:06';e.enqueue(mid,capture);receipt=e.flush()[0];check(receipt['reason']=='review_pending');check(receipt['deskMayContinue'])
 report=api('/api/match-report?edit=1&match='+mid)
 api('/api/match-report/review',{'matchId':mid,'version':report['version'],'decision':'validate','reason':''});check(True)
 e.pull();projection=fed.statistics(client,local('competition','liga-oro'));check(sum(p['goals'] for p in projection['players'])==1)
 # Local desk remains editable and its durable queue survives a network outage.
 capture['clock']='02:07';e.enqueue(mid,capture)
 real_request=e.request;e.request=Mock(side_effect=RuntimeError('offline'))
 try:e.flush()
 except RuntimeError:pass
 check(e.status()['pending']==1);e.close()
 e=ExchangeClient(base,'producer',secret,'fed.test','liga-oro',os.environ['SP_EXCHANGE_CACHE']);check(e.status()['pending']==1)
 check(e.flush()[0]['reason']=='official_locked')
 report=api('/api/match-report?edit=1&match='+mid)
 api('/api/match-report/review',{'matchId':mid,'version':report['version'],'decision':'reopen','reason':'Synthetic interoperability correction'});check(True)
 api('/api/match-report/resume',{'matchId':mid,'version':api('/api/match-report?edit=1&match='+mid)['version'],'mode':'secretariatpro'});check(True)
 e.pull();check(e.enqueue(mid,capture) is not None);check(e.flush()[0]['accepted'])
 e.pull();check(next(m for m in e.snapshot('match') if m['id']==mid)['reviewStatus']=='provisional')
 check('players' in db);check(not any('email' in p for p in db['players'].values()))
 # Customer workflow: issue in the federation UI/API, paste in Manager, choose
 # competition and persist privately. No environment configuration is changed.
 client.user_id='wizard-http-user'
 issued=api('/api/exchange/v1/invitations',{'name':'Manager HTTP test','competitions':['liga-oro'],'capture':True});check(issued['code'].startswith('SX1.'))
 verified=wizard.inspect(client,issued['code']);check(verified['competitions'][0]['name'])
 connected=wizard.finish(client,verified['ticketId'],'liga-oro');check(connected['ok'])
 managed=next(c for c in fed.configurations('ws') if c['id']==connected['id']);check(managed['managed'])
 native=fed.connect(managed)
 try:check(native.bootstrap()>0)
 finally:native.close()
 # No manual import: the authorized worker materializes and follows a real HTTP profile edit.
 worker=object.__new__(fed.FederationWorker);worker.catalog_clients={('ws',managed['id']):(client,lambda:True)};worker.errors={};worker.last_pull={};worker.contexts={}
 worker.process('ws',{});check(('ws',managed['id']) not in worker.errors)
 status=next(c for c in fed.public_status(client)['connections'] if c['id']==managed['id']);check(status['catalogPending']==0);check(bool(status['lastAppliedAt']))
 api('/api/profile',{'name':'A. Prueba','firstName':'Ana','lastName':'García Prueba','birthDate':'2001-03-04','nationality':'España','isCoach':True,'position':'Centro','bio':''},method='PUT',session=os.environ['EXCHANGE_HTTP_PLAYER_SESSION'])
 worker.last_pull={};worker.process('ws',{});check(('ws',managed['id']) not in worker.errors)
 status=next(c for c in fed.public_status(client)['connections'] if c['id']==managed['id']);check(status['catalogPending']==0);check(bool(status['lastAppliedAt']))
 athlete=db['players'][fed.local_id('ws','fed.test','player','qa-scorer')]
 check(athlete['first_name']=='Ana');check(athlete['last_name']=='García Prueba');check(athlete['birth_date']=='2001-03-04');check(athlete['nationality']=='España');check(athlete['is_coach'])
 check('2001-03-04' not in json.dumps(api('/api/match-report?match=exchange-match')))
 check(not any('storedSecret' in c for c in fed.public_status(client)['connections']))
 wizard.set_enabled(client,connected['id'],False);check(not any(c['id']==connected['id'] for c in fed.configurations('ws')))
 wizard.set_enabled(client,connected['id'],True);check(any(c['id']==connected['id'] for c in fed.configurations('ws')))
 api('/api/exchange/v1/revoke',{'id':managed['clientId']});wizard.set_enabled(client,connected['id'],False)
 try:wizard.set_enabled(client,connected['id'],True);raise AssertionError('Revocation ignored')
 except RuntimeError:check(True)

 print(f'Sports Exchange: {checks} comprobaciones reales por HTTP; cliente nativo Python ↔ servidor Astro. Sin modificar Supabase real.')
finally:e.close();fed.stop_worker()
