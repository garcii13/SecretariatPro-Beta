"""Federation-first integration boundary. Disabled unless explicitly configured.

No remote credentials or runtime settings are committed. Federation identities
are namespaced; copies in Supabase use deterministic workspace-scoped UUIDs.
"""
from __future__ import annotations
import copy
import hashlib
import json
import logging
import os
import queue
import threading
import time
import uuid
from pathlib import Path
from .client import ExchangeClient

LOG=logging.getLogger(__name__)
_service=None

def configurations(workspace):
    rows=json.loads(os.getenv('SP_FEDERATION_CONNECTIONS','[]'))
    if not isinstance(rows,list):raise ValueError('SP_FEDERATION_CONNECTIONS debe contener una lista.')
    selected=[]
    for row in rows:
        if not row.get('enabled',False) or str(row.get('workspaceId'))!=str(workspace):continue
        required={'id','url','clientId','secretEnv','namespace','competitionId','workspaceId'}
        if not required.issubset(row) or not set(row.get('modules',[]))<={'catalog','captures','statistics'}:
            raise ValueError('Configuración de federación incompleta.')
        selected.append(row)
    from .connections import stored
    return selected+stored(workspace)

def cache_path():
    from secretariat_core.app_environment import data_directory
    return Path(os.getenv('SP_EXCHANGE_CACHE') or data_directory(Path(__file__).resolve().parents[2])/'federation_exchange'/'cache.sqlite')

def connect(config):
    from .connections import secret
    return ExchangeClient(config['url'],config['clientId'],secret(config),config['namespace'],config['competitionId'],cache_path(),config.get('sourceNamespace'))

def local_id(workspace,namespace,kind,external):
    return str(uuid.uuid5(uuid.NAMESPACE_URL,json.dumps([workspace,namespace,kind,str(external)],separators=(',',':'))))

def connection_for(client,ident):
    workspace=str(client._active_workspace_id())
    config=next((c for c in configurations(workspace) if c['id']==ident),None)
    if not config:raise ValueError('Conexión no disponible en este espacio.')
    return config

def public_status(client):
    from .connections import stored
    output=[]
    configs=configurations(client._active_workspace_id())
    configs += [c for c in stored(client._active_workspace_id(),True) if not c['enabled']]
    for config in configs:
        try:
            exchange=connect(config)
            try:status=exchange.status()
            finally:exchange.close()
            output.append({'id':config['id'],'name':config.get('name') or config['namespace'],'competitionName':config.get('competitionName') or config['competitionId'],'enabled':config.get('enabled',True),'managed':config.get('managed',False),'modules':config.get('modules',[]),**status,'message':(_service.errors.get((str(client._active_workspace_id()),config['id']),'')) if _service else ''})
        except Exception:output.append({'id':config['id'],'namespace':config['namespace'],'configured':False,'message':'No se pudo verificar la conexión. Solicita una nueva invitación a tu federación.'})
    return {'schema':'sports.exchange.v1','playerAuthority':'federation','connections':output,'independent':True}

def synchronise(client,ident):
    config=connection_for(client,ident);exchange=connect(config)
    try:
        count=exchange.pull();receipts=exchange.flush()
        global _service
        if _service is None:_service=FederationWorker()
        _service.submit(client._active_workspace_id(),{})
        return {'changed':count,'receipts':receipts,**exchange.status()}
    finally:exchange.close()

def export_snapshot(client,ident):
    config=connection_for(client,ident);exchange=connect(config)
    try:
        entities=[]
        for row in exchange.db.execute('SELECT kind,id,revision,payload FROM entities WHERE scope=? ORDER BY kind,id',(exchange.scope,)):
            entities.append({'kind':row[0],'id':row[1],'revision':row[2],'data':json.loads(row[3])})
        cursor=exchange.db.execute('SELECT cursor FROM meta WHERE scope=?',(exchange.scope,)).fetchone()
        return {'schema':'sports.exchange.v1','namespace':config['namespace'],'competitionId':config['competitionId'],'entities':entities,'nextCursor':cursor[0] if cursor else '0'}
    finally:exchange.close()

def manager_capture(client,context):
    """Called after Manager persisted its act; same worker and source adapter as Live."""
    try:
        match=context.get('match') or {};workspace=client._active_workspace_id()
        if not configurations(workspace):return
        home=str(match.get('home_team_id') or '');away=str(match.get('away_team_id') or '')
        match={**match,'home_team':{'id':home},'away_team':{'id':away}}
        rosters={'team1':context.get('home_roster',[]),'team2':context.get('away_roster',[])}
        saved={'online':{'match':match,'rosters':rosters,'attendance':{k:[str(r['player_id']) for r in rows] for k,rows in rosters.items()},'events':context.get('events',[])},
               'scores':{'team1_score':match.get('home_score'),'team2_score':match.get('away_score'),'time':'00:00'},'state':{'match':{}}}
        global _service
        if _service is None:_service=FederationWorker()
        _service.submit(workspace,saved)
    except Exception:LOG.warning('Entrega federativa de Manager pendiente; el acta local queda conservada.')

def assert_local_write(client,kind,ident):
    """Federation-owned sporting fields are read-only while connected.

    Disabling the optional connection allows an independent local continuation;
    no existing unconnected competition is subject to these restrictions.
    """
    for config in configurations(client._active_workspace_id()):
        exchange=connect(config)
        try:
            try:exchange.mapped(kind,str(ident),reverse=True)
            except ValueError:continue
            raise PermissionError('Este dato deportivo procede de la federación. Corrígelo en origen y sincroniza el catálogo.')
        finally:exchange.close()

def statistics(client,competition_id,current_snapshot=None):
    workspace=client._active_workspace_id()
    for config in configurations(workspace):
        if 'statistics' not in config.get('modules',[]):continue
        exchange=connect(config)
        try:
            try:external=exchange.mapped('competition',competition_id,reverse=True)
            except ValueError:continue
            if external!=config['competitionId']:continue
            matches={m['id']:m for m in exchange.snapshot('match') if m.get('reviewStatus')=='official'}
            provisional=False
            if current_snapshot:
                try:
                    mid,live=convert_capture(current_snapshot,exchange)
                    if live['matchStatus'] in ('live','finished'):
                        matches[mid]={**live,**live['report'],'id':mid,'reviewStatus':'provisional'};provisional=True
                except ValueError:pass
            teams={t['id']:t for t in exchange.snapshot('team')};competitions=exchange.snapshot('competition')
            if not competitions:return None
            c=competitions[0];players={};keepers={};table={}
            def local(kind,ident):return exchange.mapped(kind,ident)
            for tid,t in teams.items():table[tid]={'team_id':local('team',tid),'team_name':t['name'],'played':0,'wins':0,'draws':0,'losses':0,'goals_for':0,'goals_against':0,'goal_difference':0,'points':0}
            for m in matches.values():
                for e in m.get('events',[]):
                    if e['type']!='goal' or e.get('ownGoal') or e.get('shootout'):continue
                    names={(r['teamId'],r['playerId']):r['name'] for r in m.get('lineup',[])}
                    for pid,field in ((e['playerId'],'goals'),(e.get('assistantId'),'assists')):
                        if not pid:continue
                        key=(e['teamId'],pid);row=players.setdefault(key,{'team_id':local('team',key[0]),'player_id':local('player',pid),'goals':0,'assists':0,'points':0,'player':{'id':local('player',pid),'display_name':names.get(key,'')}})
                        row[field]+=1;row['points']=row['goals']+row['assists']
                for k in m.get('keepers',[]):
                    key=(k['teamId'],k['playerId']);row=keepers.setdefault(key,{'team_id':local('team',key[0]),'player_id':local('player',key[1]),'seconds':0,'shots':0,'saves':0})
                    for field in ('seconds','shots','saves'):row[field]+=k[field]
                if m.get('matchStatus')!='finished' or m.get('home') is None or m.get('away') is None:continue
                for tid,gf,ga in ((m['homeTeamId'],m['home'],m['away']),(m['awayTeamId'],m['away'],m['home'])):
                    row=table[tid];row['played']+=1;row['goals_for']+=gf;row['goals_against']+=ga;row['goal_difference']=row['goals_for']-row['goals_against']
                    result='wins' if gf>ga else 'draws' if gf==ga else 'losses';row[result]+=1
                    row['points']+=int(c.get('pointsWin',2) if gf>ga else c.get('pointsDraw',1) if gf==ga else c.get('pointsLoss',0))
            ordered=sorted(table.values(),key=lambda r:(-r['points'],-r['goal_difference'],-r['goals_for'],r['team_name']))
            for i,r in enumerate(ordered):r['position']=i+1
            leaders={}
            for row in sorted(players.values(),key=lambda r:(-r['points'],-r['goals'],r['player']['display_name'])):leaders.setdefault(row['team_id'],row)
            for row in keepers.values():row['savePercentage']=100*row['saves']/row['shots'] if row['shots'] else None
            return {'namespace':config['namespace'],'standings':ordered,'leaders':leaders,'players':list(players.values()),'keepers':list(keepers.values()),'provisionalIncluded':provisional}
        finally:exchange.close()
    return None

def catalog_plan(client,ident):
    client._require_competition_manager()
    config=connection_for(client,ident)
    if 'catalog' not in config.get('modules',[]):raise PermissionError('La importación del catálogo no está activada.')
    exchange=connect(config)
    try:
        competitions=exchange.snapshot('competition');teams=exchange.snapshot('team');rosters=exchange.snapshot('roster');matches=exchange.snapshot('match')
        if not competitions:raise ValueError('Sincroniza antes el catálogo de la federación.')
        return {'namespace':config['namespace'],'competition':competitions[0], 'teams':teams,'rosters':rosters,'matches':matches,
                'counts':{'teams':len(teams),'players':len({p['id'] for r in rosters for p in r['players']}),'rosters':len(rosters),'matches':len(matches)},
                'policy':'La federación controla identidad deportiva, roster y calendario. No se importan cuentas ni se sustituyen eventos locales.'}
    finally:exchange.close()

def import_catalog(client,ident,authorize=None):
    # Deliberately explicit, owner/competition-manager operation, using the existing
    # authenticated Supabase client and its RLS. No service_role and no new grants.
    plan=catalog_plan(client,ident);config=connection_for(client,ident);workspace=client._active_workspace_id();exchange=connect(config)
    def uid(kind,external):return local_id(workspace,config['namespace'],kind,external)
    def upsert(table,kind,external,payload):
        ident=uid(kind,external)
        response=client.client.table(table).upsert({'id':ident,'workspace_id':workspace,**payload}).execute()
        if not response.data:raise RuntimeError('La federación no pudo materializarse en el espacio activo.')
        exchange.bind(kind,str(external),ident)
        return ident
    try:
        c=plan['competition'];season=upsert('seasons','season',c['season'],{'name':c['season']})
        comp=upsert('competitions','competition',c['id'],{'name':c['name'],'season_id':season,'category':c.get('category') or '', 'active':True,'points_win':c.get('pointsWin',2),'points_draw':c.get('pointsDraw',1),'points_loss':c.get('pointsLoss',0)})
        # Only federation-owned identity fields are refreshed. Photos, colours,
        # flags, themes, operators, OBS settings and local events remain local.
        for t in plan['teams']:upsert('teams','team',t['id'],{'name':t['name'],'short_name':t.get('shortName') or t['name'][:12]})
        people={}
        for r in plan['rosters']:
            for p in r['players']:
                previous=people.get(p['id'])
                if previous and previous['name']!=p['name']:raise ValueError('Identidad federativa ambigua entre rosters; revisa el catálogo.')
                people[p['id']]=p
        for match in plan['matches']:
            for p in match.get('lineup',[]):
                people.setdefault(p['playerId'],{'id':p['playerId'],'name':p['name'],'position':p.get('position','')})
        position_map={'Portería':'goalkeeper','Defensa':'defender','Centro':'midfielder','Delantera':'forward'}
        for p in people.values():upsert('players','player',p['id'],{'display_name':p['name'],'first_name':p['name'],'last_name':'','position':position_map.get(p.get('position'),p.get('position') or None),'is_coach':False})
        for r in plan['rosters']:
            tid=uid('team',r['teamId'])
            client.manager_create_roster_group(tid,comp)
            # Remove only memberships previously imported by this connector, before
            # number swaps. A local membership with the same number causes a visible
            # conflict; it is never silently reassigned by a name match.
            existing=client.manager_list_team_rosters(tid,comp)
            for old in existing:
                try:external=exchange.mapped('membership',str(old['id']),reverse=True)
                except ValueError:continue
                client.client.table('rosters').update({'active':False}).eq('id',old['id']).eq('workspace_id',workspace).execute()
            for p in r['players']:
                if p.get('number') is None:continue
                external=r['id']+':'+p['id']
                upsert('rosters','membership',external,{'competition_id':comp,'team_id':tid,'player_id':uid('player',p['id']),'shirt_number':p['number'],'member_type':'player','captain':False,'active':not r.get('archived',False)})
            exchange.bind('roster',r['id'],uid('roster',r['id']))
        # Dropped federation memberships remain inactive; local events/history survive.
        for m in plan['matches']:
            ident=uid('match',m['id']);existing=client.client.table('matches').select('id').eq('id',ident).eq('workspace_id',workspace).execute().data
            schedule={'competition_id':comp,'home_team_id':uid('team',m['homeTeamId']),'away_team_id':uid('team',m['awayTeamId']),'match_date':m['startsAt'],'venue':m.get('venue') or ''}
            if existing:
                client.client.table('matches').update(schedule).eq('id',ident).eq('workspace_id',workspace).execute();exchange.bind('match',m['id'],ident)
            else:upsert('matches','match',m['id'],{**schedule,'status':'scheduled','home_score':0,'away_score':0})
        global _service
        if config.get('autoImport',False) and authorize is not None:
            if _service is None:_service=FederationWorker()
            _service.catalog_clients[(str(workspace),config['id'])]=(client,authorize)
            if str(workspace) not in _service.contexts:_service.submit(workspace,{})
        return {'ok':True,**plan['counts'],'competitionId':comp,'namespace':config['namespace']}
    finally:exchange.close()

def convert_capture(snapshot,exchange):
    online=snapshot.get('online') or {};match=online.get('match') or {};scores=snapshot.get('scores') or {}
    mid=exchange.mapped('match',match.get('id'),reverse=True)
    report={'lineup':[],'events':[],'keepers':[]}
    for side in ('team1','team2'):
        team=match.get('home_team' if side=='team1' else 'away_team') or {}
        tid=exchange.mapped('team',team.get('id'),reverse=True)
        called=set((online.get('attendance') or {}).get(side,[]))
        for row in (online.get('rosters') or {}).get(side,[]):
            pid=str(row.get('player_id') or (row.get('player') or {}).get('id') or '')
            if row.get('member_type')=='coach' or pid not in called:continue
            player=row.get('player') or {};external=exchange.mapped('player',pid,reverse=True)
            report['lineup'].append({'teamId':tid,'playerId':external,'name':player.get('display_name') or ' '.join(str(player.get(k) or '') for k in ('first_name','last_name')).strip(),'number':int(row['shirt_number']),'position':str(player.get('position') or '')})
    rows=sorted((e for e in online.get('events',[]) if not e.get('cancelled_at')),key=lambda e:(str(e.get('created_at') or ''),str(e.get('id') or '')))
    assists={str(e.get('related_event_id')):str(e.get('player_id') or '') for e in rows if e.get('event_type')=='assist'}
    import re
    for e in rows:
        if e.get('event_type') not in ('goal','penalty'):continue
        clock=str(e.get('match_time') or '')
        if not re.fullmatch(r'\d{1,3}:[0-5]\d',clock):raise ValueError('Una jugada no tiene reloj válido; la mesa sigue funcionando y el envío queda pendiente de corrección.')
        mm,ss=map(int,clock.split(':'));pid=exchange.mapped('player',str(e.get('player_id') or ''),reverse=True)
        assistant=assists.get(str(e['id']))
        report['events'].append({'id':str(e['id']),'teamId':exchange.mapped('team',str(e.get('team_id') or ''),reverse=True),'type':e['event_type'],'seconds':mm*60+ss,'period':str(e.get('period') or ''),'sequence':len(report['events'])+1,'timeBasis':'source_clock','playerId':pid,'assistantId':exchange.mapped('player',assistant,reverse=True) if assistant else '', 'ownGoal':bool(e.get('own_goal',False)),'shootout':bool(e.get('shootout',False)),'penaltyType':str(e.get('penalty_type') or '2') if e['event_type']=='penalty' else ''})
    status={'in_progress':'live','completed':'finished','final':'finished'}.get(match.get('status'),match.get('status') or 'scheduled')
    # Event entry itself means the desk has started even if its local match row
    # remains scheduled until finish_match. Closing the desk is never required.
    if status=='scheduled' and rows:status='live'
    return mid,{'homeTeamId':exchange.mapped('team',(match.get('home_team') or {}).get('id'),reverse=True),'awayTeamId':exchange.mapped('team',(match.get('away_team') or {}).get('id'),reverse=True),'matchStatus':status,'home':int(scores.get('team1_score') or 0),'away':int(scores.get('team2_score') or 0),'clock':str(scores.get('time') or '00:00'),'period':str((snapshot.get('state') or {}).get('match',{}).get('period') or ''),'report':report}

def sporting_snapshot(snapshot):
    online=snapshot.get('online') or {}
    # Explicit allowlist; never enqueue account, device, camera, OCR or OBS state.
    return {'online':{key:copy.deepcopy(online.get(key)) for key in ('match','rosters','attendance','events')},
            'scores':{key:(snapshot.get('scores') or {}).get(key) for key in ('team1_score','team2_score','time')},
            'state':{'match':{'period':(snapshot.get('state') or {}).get('match',{}).get('period')}}}

class FederationWorker:
    def __init__(self):
        self.jobs=queue.Queue(maxsize=32);self.stop=threading.Event();self.contexts={};self.errors={};self.catalog_clients={}
        self.thread=threading.Thread(target=self.run,name='sports-exchange',daemon=True);self.thread.start()
    def submit(self,workspace,snapshot):
        configs=configurations(workspace)
        if not configs:return
        payload=(workspace,sporting_snapshot(snapshot))
        try:self.jobs.put_nowait(payload)
        except queue.Full:
            # Full snapshots supersede old unsent wakeups, not durable deliveries.
            try:self.jobs.get_nowait()
            except queue.Empty:pass
            self.jobs.put_nowait(payload)
    def run(self):
        while not self.stop.is_set():
            try:workspace,snapshot=self.jobs.get(timeout=1)
            except queue.Empty:workspace=None;snapshot=None
            if workspace:self.contexts[workspace]=snapshot
            # Coalesce wakeups after an outage. Each snapshot contains the full
            # persisted event list, so corrections and cancellations survive.
            while True:
                try:ws,latest=self.jobs.get_nowait();self.contexts[ws]=latest
                except queue.Empty:break
            for ws,saved in list(self.contexts.items()):
                try:configs=configurations(ws)
                except Exception:continue
                for config in configs:
                    exchange=None
                    try:
                        exchange=connect(config)
                        if 'captures' in config.get('modules',[]):
                            try:mid,data=convert_capture(saved,exchange)
                            except ValueError:
                                if (saved.get('online') or {}).get('match'):raise
                                mid=None
                            if mid:exchange.enqueue(mid,data)
                        exchange.flush()
                        key=(ws,config['id']);last=getattr(self,'last_pull',{})
                        if time.monotonic()-last.get(key,0)>5:
                            count=exchange.pull();last[key]=time.monotonic();self.last_pull=last
                            registration=self.catalog_clients.get(key)
                            client,authorized=registration if registration else (None,None)
                            if count and config.get('autoImport',False) and client is not None and authorized() and str(client._active_workspace_id())==str(ws):
                                # Reuses current authenticated workspace/RLS. A
                                # revoked/expired Manager session cannot import.
                                client._require_competition_manager()
                                import_catalog(client,config['id'],authorized)
                        self.errors.pop(key,None)
                    except Exception:self.errors[(ws,config['id'])]='Conexión pendiente; la mesa continúa de forma independiente.'
                    finally:
                        if exchange:exchange.close()
    def close(self):self.stop.set();self.thread.join(timeout=1)

def observe_runtime(runtime,snapshot):
    global _service
    try:
        workspace=str((getattr(runtime,'active_workspace',None) or {}).get('id') or '')
        if not workspace or not configurations(workspace):return
        if _service is None:_service=FederationWorker()
        _service.submit(workspace,snapshot)
    except Exception:LOG.warning('Integración deportiva pendiente; se mantiene la operación local.')

def stop_worker():
    global _service
    if _service:_service.close();_service=None
