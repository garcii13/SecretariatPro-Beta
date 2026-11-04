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
_catalog_lock=threading.RLock()

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
            try:
                status=exchange.status();applied=exchange.applied(client._active_workspace_id())
                status['lastAppliedAt']=applied['at'] if applied else None
                status['automatic']=config.get('autoImport',False)
                status.update(exchange.catalog_health(client._active_workspace_id()))
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
        _service.contexts.setdefault(str(client._active_workspace_id()),{})
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
            raise PermissionError('Este dato deportivo procede de la federación. Corrígelo en origen; se actualizará automáticamente.')
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

def player_payload(p):
    import datetime,unicodedata
    p=dict(p)
    for field in ('firstName','lastName','nationality'):
        if p.get(field) is None and field in p:p[field]=''
    if p.get('isCoach') is None and 'isCoach' in p:p['isCoach']=False
    if not isinstance(p.get('name'),str) or not p['name'].strip():raise ValueError('El jugador no tiene un nombre válido.')
    for field in ('firstName','lastName','nationality'):
        if field in p and not isinstance(p[field],str):raise ValueError('La ficha del jugador tiene un campo de texto no válido.')
    if 'isCoach' in p and type(p['isCoach']) is not bool:raise ValueError('La etiqueta de entrenador no es válida.')
    aliases={'portería':'goalkeeper','porteria':'goalkeeper','goalkeeper':'goalkeeper','defensa':'defender','defender':'defender','centro':'centre','centre':'centre','center':'centre','midfielder':'centre','delantera':'forward','delantero':'forward','forward':'forward','unknown':'unknown'}
    aliases.update({'portero':'goalkeeper','guardameta':'goalkeeper','goalie':'goalkeeper','malvakt':'goalkeeper','brankar':'goalkeeper','maalivahti':'goalkeeper','torhuter':'goalkeeper','defensor':'defender','forsvarare':'defender','back':'defender','obrance':'defender','puolustaja':'defender','verteidiger':'defender','centr':'centre','keskushyokkaaja':'centre','mittelsturmer':'centre','anfallare':'forward','utocnik':'forward','hyokkaaja':'forward','sturmer':'forward'})
    position=''.join(c for c in unicodedata.normalize('NFKD',str(p.get('position') or '').strip().lower()) if not unicodedata.combining(c))
    result={'display_name':p['name'].strip(),'first_name':p.get('firstName') or p['name'],'last_name':p.get('lastName') or '', 'position':aliases.get(position,'unknown'),'is_coach':bool(p.get('isCoach',False))}
    if 'birthDate' in p:
        birth=p['birthDate'].strip() if isinstance(p['birthDate'],str) else p['birthDate']
        birth=birth or None
        if birth:
            try:
                date=datetime.date.fromisoformat(birth)
                if date.isoformat()!=birth or date<datetime.date(1900,1,1) or date>datetime.date.today():raise ValueError()
            except (ValueError,TypeError):raise ValueError('Fecha de nacimiento no válida en el catálogo federativo.') from None
        result['birth_date']=birth
    if 'nationality' in p:result['nationality']=p['nationality'] or None
    return result

def import_catalog(client,ident,authorize=None):
    with _catalog_lock:return _import_catalog(client,ident,authorize)

def _import_catalog(client,ident,authorize=None):
    # Independent entity checkpoints: one rejected player must not stop the calendar.
    plan=catalog_plan(client,ident);config=connection_for(client,ident);workspace=client._active_workspace_id();exchange=connect(config)
    issues=[]
    labels={'player':{},'team':{str(t['id']):t['name'] for t in plan['teams']},'competition':{str(plan['competition']['id']):plan['competition']['name']}}
    for roster in plan['rosters']:
        for player in roster['players']:labels['player'].setdefault(str(player['id']),player['name'])
    def check():
        if str(client._active_workspace_id())!=str(workspace) or (authorize is not None and not authorize()):raise PermissionError('La sesión o el espacio de trabajo cambió. Vuelve a iniciar sesión.')
        client._require_competition_manager()
    def uid(kind,external):return local_id(workspace,config['namespace'],kind,external)
    def problem(kind,external,code,message,level='error'):
        issues.append({'kind':kind,'id':str(external),'code':code,'message':message,'level':level,'label':labels.get(kind,{}).get(str(external),str(external))})
    def fail(kind,external,exc):
        if isinstance(exc,PermissionError):raise exc
        code=str(getattr(exc,'code','') or 'write_pending')
        message={'23514':'El registro no cumple las reglas de destino. Corrige el dato en la federación.', '23505':'El registro entra en conflicto con un dato local. Revisa su identidad o dorsal.', '23503':'Falta una referencia de equipo, jugador o competición.'}.get(code,'No se pudo actualizar este registro. Se reintentará automáticamente.')
        problem(kind,external,code,message)
    def upsert(table,kind,external,payload):
        check();local=uid(kind,external);section='record:'+kind+':'+str(external)
        digest=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        try:
            if exchange.section_digest(workspace,section)!=digest:
                response=client.client.table(table).upsert({'id':local,'workspace_id':workspace,**payload}).execute()
                if not response.data:raise RuntimeError('write_pending')
                exchange.bind(kind,str(external),local);exchange.mark_section(workspace,section,digest)
            else:exchange.bind(kind,str(external),local)
            return local
        except Exception as exc:fail(kind,external,exc);return None
    def finish(digest):
        check();exchange.mark_health(workspace,issues)
        pending=sum(i['level']=='error' for i in issues)
        if not pending:exchange.mark_applied(workspace,digest)
        return {'ok':not pending,**plan['counts'],'competitionId':uid('competition',plan['competition']['id']),'namespace':config['namespace'],'pending':pending,'issues':issues}
    try:
        check();digest=exchange.catalog_digest();people={};invalid=set();roster_errors={}
        # Validate and normalize before modifying a roster. Unknown optional positions
        # are stored as unknown, but invalid identities/dates remain pending in isolation.
        for r in plan['rosters']:
            numbers=set()
            for source in r['players']:
                p=copy.deepcopy(source);pid=p['id'];number=p.get('number')
                if isinstance(number,str) and number.strip().isascii() and number.strip().isdigit():number=int(number.strip())
                p['number']=number
                if number is not None:
                    if type(number) is not int or not 0<=number<=99 or number in numbers:roster_errors[r['id']]='Dorsales repetidos o no válidos en el roster federativo.'
                    numbers.add(str(number)) if type(number) is not int else numbers.add(number)
                previous=people.get(pid)
                if previous and any(previous.get(k)!=p.get(k) for k in ('name','firstName','lastName','birthDate','nationality','isCoach')):
                    invalid.add(pid);problem('player',pid,'ambiguous_identity','Identidad federativa ambigua entre rosters; revisa el catálogo.')
                people[pid]=p
        for match in plan['matches']:
            for p in match.get('lineup',[]):people.setdefault(p['playerId'],{'id':p['playerId'],'name':p['name'],'position':p.get('position','')})
        players={}
        for pid,p in people.items():
            if pid in invalid:continue
            try:
                players[pid]=player_payload(p)
                if p.get('position') and players[pid]['position']=='unknown' and str(p['position']).strip().lower()!='unknown':problem('player',pid,'position_unknown','Posición no reconocida; guardada como desconocida sin bloquear la actualización.','warning')
            except ValueError as exc:invalid.add(pid);problem('player',pid,'invalid_player',str(exc))
        c=plan['competition'];season=upsert('seasons','season',c['season'],{'name':c['season']})
        if not season:return finish(digest)
        comp=upsert('competitions','competition',c['id'],{'name':c['name'],'season_id':season,'category':c.get('category') or '', 'active':True,'points_win':c.get('pointsWin',2),'points_draw':c.get('pointsDraw',1),'points_loss':c.get('pointsLoss',0)})
        if not comp:return finish(digest)
        teams={t['id']:upsert('teams','team',t['id'],{'name':t['name'],'short_name':t.get('shortName') or t['name'][:12]}) for t in plan['teams']}
        for pid,payload in players.items():
            source=people[pid]
            # Missing optional profile fields in an older provider are not commands
            # to erase a richer existing local identity.
            missing={column for field,column in (('firstName','first_name'),('lastName','last_name'),('isCoach','is_coach')) if field not in source}
            if missing:
                check()
                try:
                    existing=client.client.table('players').select('id').eq('id',uid('player',pid)).eq('workspace_id',workspace).execute().data
                    if existing:payload={k:v for k,v in payload.items() if k not in missing}
                except Exception as exc:fail('player',pid,exc);invalid.add(pid);continue
            if not upsert('players','player',pid,payload):invalid.add(pid)
        for source in plan['rosters']:
            r={**source,'players':[{**p,'number':int(p['number'].strip()) if isinstance(p.get('number'),str) and p['number'].strip().isascii() and p['number'].strip().isdigit() else p.get('number')} for p in source['players']]}
            rid=r['id'];check()
            if rid in roster_errors:problem('roster',rid,'invalid_roster',roster_errors[rid]);continue
            if not teams.get(r['teamId']) or any(p['id'] in invalid for p in r['players']):
                problem('roster',rid,'dependency_pending','Roster pendiente de corregir un jugador o equipo. Se conserva la última copia válida.');continue
            tid=uid('team',r['teamId'])
            memberships=sorted([{'id':p['id'],'number':p.get('number'),'type':'coach' if p.get('isCoach') and player_payload(p)['position']=='unknown' else 'player'} for p in r['players']],key=lambda p:p['id'])
            roster_digest=hashlib.sha256(json.dumps([r.get('archived',False),memberships],sort_keys=True).encode()).hexdigest();section='roster:'+rid
            if exchange.section_digest(workspace,section)==roster_digest:continue
            try:
                existing=client.manager_list_team_rosters(tid,comp)
                imported=[]
                expected={uid('membership',rid+':'+p['id']):rid+':'+p['id'] for p in r['players']}
                for old in existing:
                    try:exchange.mapped('membership',str(old['id']),reverse=True);imported.append(old)
                    except ValueError:
                        if str(old['id']) in expected:
                            exchange.bind('membership',expected[str(old['id'])],str(old['id']));imported.append(old)
                        elif any(p.get('number')==old.get('shirt_number') for p in r['players']):raise ValueError('Un dorsal del roster está ocupado por un registro local. Revisa la vinculación.')
                client.manager_create_roster_group(tid,comp)
                captains=exchange.journal(workspace,section) or {str(old['id']):bool(old.get('captain',False)) for old in existing}
                exchange.write_journal(workspace,section,captains)
                for old in imported:
                    check();client.client.table('rosters').update({'active':False}).eq('id',old['id']).eq('workspace_id',workspace).execute()
                for p in r['players']:
                    if p.get('number') is None:continue
                    external=rid+':'+p['id'];check()
                    # Membership writes run after deactivation even if their data digest
                    # was seen before; this preserves number swaps on a retry.
                    payload={'id':uid('membership',external),'workspace_id':workspace,'competition_id':comp,'team_id':tid,'player_id':uid('player',p['id']),'shirt_number':p['number'],'member_type':'coach' if p.get('isCoach') and players[p['id']]['position']=='unknown' else 'player','captain':captains.get(uid('membership',external),False),'active':not r.get('archived',False)}
                    response=client.client.table('rosters').upsert(payload).execute()
                    if not response.data:raise RuntimeError('write_pending')
                    exchange.bind('membership',external,payload['id'])
                exchange.bind('roster',rid,uid('roster',rid));exchange.mark_section(workspace,section,roster_digest);exchange.clear_journal(workspace,section)
            except Exception as exc:
                if isinstance(exc,ValueError):problem('roster',rid,'invalid_roster',str(exc))
                else:fail('roster',rid,exc)
        for m in plan['matches']:
            check();mid=m['id']
            if not teams.get(m['homeTeamId']) or not teams.get(m['awayTeamId']):problem('match',mid,'dependency_pending','Partido pendiente de un equipo válido. Se conserva el calendario anterior.');continue
            schedule={'competition_id':comp,'home_team_id':uid('team',m['homeTeamId']),'away_team_id':uid('team',m['awayTeamId']),'match_date':m['startsAt'],'venue':m.get('venue') or ''}
            section='schedule:'+mid;mark=hashlib.sha256(json.dumps(schedule,sort_keys=True).encode()).hexdigest()
            if exchange.section_digest(workspace,section)==mark:continue
            try:
                local=uid('match',mid);existing=client.client.table('matches').select('id').eq('id',local).eq('workspace_id',workspace).execute().data
                if existing:
                    check();client.client.table('matches').update(schedule).eq('id',local).eq('workspace_id',workspace).execute();exchange.bind('match',mid,local)
                elif not upsert('matches','match',mid,{**schedule,'status':'scheduled','home_score':0,'away_score':0}):continue
                exchange.mark_section(workspace,section,mark)
            except Exception as exc:fail('match',mid,exc)
        return finish(digest)
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

def ensure_automatic(client,authorize):
    """Register the current authenticated Manager session; no network on the UI thread."""
    global _service
    workspace=str(client._active_workspace_id())
    configs=[c for c in configurations(workspace) if c.get('autoImport') and 'catalog' in c.get('modules',[])]
    if not configs:return
    if _service is None:_service=FederationWorker()
    for config in configs:_service.catalog_clients[(workspace,config['id'])]=(client,authorize)
    _service.contexts.setdefault(workspace,{})

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
            for ws,saved in list(self.contexts.items()):self.process(ws,saved)
    def process(self,ws,saved):
        try:configs=configurations(ws)
        except Exception:return
        for config in configs:
            exchange=None
            try:
                exchange=connect(config)
                key=(ws,config['id']);last=getattr(self,'last_pull',{})
                if time.monotonic()-last.get(key,0)>5:
                    # Pull first: an unlinked Live match must not block catalogue repair.
                    last[key]=time.monotonic();self.last_pull=last
                    exchange.pull()
                    registration=self.catalog_clients.get(key)
                    client,authorized=registration if registration else (None,None)
                    applied=exchange.applied(ws)
                    if config.get('autoImport') and client is not None and authorized() and str(client._active_workspace_id())==str(ws) and (not applied or applied['digest']!=exchange.catalog_digest() or exchange.catalog_health(ws)['catalogPending']):
                        # Retry a failed materialization even if the next feed is empty.
                        import_catalog(client,config['id'],authorized)
                capture_error=False
                if 'captures' in config.get('modules',[]):
                    try:mid,data=convert_capture(saved,exchange)
                    except ValueError:
                        mid=None;capture_error=bool((saved.get('online') or {}).get('match'))
                    if mid:exchange.enqueue(mid,data)
                exchange.flush()
                if capture_error:
                    self.errors[key]='Mesa sin vincular: el catálogo se actualiza, pero sus jugadas aún no se pueden enviar.'
                    continue
                self.errors.pop(key,None)
            except Exception as exc:
                self.errors[(ws,config['id'])]='Actualización pendiente; se reintentará automáticamente. La mesa continúa de forma independiente.'
                if isinstance(exc,ValueError):self.errors[(ws,config['id'])]=str(exc)
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
