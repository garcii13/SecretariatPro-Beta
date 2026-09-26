"""Season-scoped people/fixture imports with read-only previews."""
from __future__ import annotations
import csv
import io
import unicodedata
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo
from collections import defaultdict
from threading import RLock

IMPORT_LOCK = RLock()

def key(value):
    return ' '.join(unicodedata.normalize('NFKC', str(value or '')).casefold().split())

def read_rows(filename, content, kind):
    from manager_api.main import normalized_header, player_rows_to_dataset
    if filename.lower().endswith('.csv'):
        text=content.decode('utf-8-sig')
        try: dialect=csv.Sniffer().sniff(text[:4096],delimiters=',;\t')
        except csv.Error: dialect=csv.excel
        sheets=[('CSV',list(csv.reader(io.StringIO(text),dialect)))]
    else:
        from openpyxl import load_workbook
        book=load_workbook(io.BytesIO(content),read_only=True,data_only=True)
        try: sheets=[(s.title,list(s.values)) for s in book.worksheets]
        finally: book.close()
    aliases={'equipo':'team_name','club':'team_name','team':'team_name','team_name':'team_name',
             'fecha':'date','fecha partido':'date','date':'date','match_date':'date',
             'hora':'time','horario':'time','time':'time','instalacion':'venue','instalación':'venue','pabellon':'venue','pabellón':'venue','venue':'venue',
             'local':'home','equipo local':'home','home':'home','home_team':'home','home_team_code':'home',
             'visitante':'away','equipo visitante':'away','away':'away','away_team':'away','away_team_code':'away'}
    output=[]
    for sheet,rows in sheets:
        if not rows: continue
        headers=list(rows[0])
        mapped=[aliases.get(key(h),aliases.get(normalized_header(h),normalized_header(h))) for h in headers]
        for number,values in enumerate(rows[1:],2):
            if not any(v not in (None,'') for v in values): continue
            raw={mapped[i]:v for i,v in enumerate(values) if i<len(mapped)}
            if kind=='people':
                personal=player_rows_to_dataset(sheet,[headers,list(values)],roster=True)['rows']
                row=personal[0] if personal else {}
                row['team_name']=str(raw.get('team_name') or '').strip()
            else: row=raw
            output.append({'sheet':sheet,'row':number,'data':row})
    return output

def schedule(row,tz_name):
    zone=ZoneInfo(tz_name)
    value=row.get('date'); parsed=None
    if isinstance(value,datetime): parsed=value
    elif isinstance(value,date): parsed=datetime.combine(value,time())
    else:
        text=str(value or '').strip()
        for fmt in ('%Y-%m-%d','%d/%m/%Y','%d-%m-%Y','%Y-%m-%dT%H:%M:%S','%Y-%m-%d %H:%M:%S','%d/%m/%Y %H:%M','%Y-%m-%d %H:%M'):
            try: parsed=datetime.strptime(text,fmt);break
            except ValueError: pass
    if parsed is None: raise ValueError('Fecha inválida: utiliza DD/MM/AAAA o AAAA-MM-DD')
    clock=row.get('time'); known=clock not in (None,'') or parsed.time()!=time()
    if clock not in (None,''):
        if isinstance(clock,datetime): clock=clock.time()
        if isinstance(clock,time): clock=clock.replace(tzinfo=None)
        else:
            value=str(clock).strip();clock=None
            for fmt in ('%H:%M','%H:%M:%S'):
                try: clock=datetime.strptime(value,fmt).time();break
                except ValueError: pass
            if clock is None: raise ValueError('Hora inválida: utiliza HH:MM o deja la celda vacía')
        parsed=datetime.combine(parsed.date(),clock)
    local=parsed.replace(tzinfo=zone)
    utc=local.astimezone(timezone.utc)
    if utc.astimezone(zone).replace(tzinfo=None)!=parsed:
        raise ValueError('La hora no existe por el cambio de horario')
    return utc.isoformat(),known

def preview(client,kind,rows,competition_id,season_id,tz_name):
    competitions=client.manager_list_competitions()
    comp=next((x for x in competitions if str(x['id'])==competition_id),None)
    if not comp or str(comp.get('season_id') or '')!=season_id or not season_id:
        raise ValueError('Selecciona una competición de la temporada indicada')
    if not any(str(s['id'])==season_id for s in client.manager_list_seasons()):
        raise ValueError('Temporada no disponible')
    teams=client.manager_list_teams(); index=defaultdict(dict)
    for team in teams:
        for value in (team.get('name'),team.get('short_name')):
            if value: index[key(value)][str(team['id'])]=team
    groups={str(g['team_id']) for g in client.manager_list_roster_groups() if str(g['competition_id'])==competition_id} if kind=='people' else set()
    missing_teams={};missing_rosters={}; errors=[];prepared=[]; roster_cache={}
    def resolve(name,entry):
        options=list(index.get(key(name),{}).values())
        if not name: raise ValueError('Falta el equipo')
        if not options:
            missing_teams[key(name)]=str(name)
            raise ValueError(f'El equipo «{name}» no existe')
        if len(options)>1: raise ValueError(f'Equipo ambiguo: «{name}». Utiliza su nombre completo')
        return options[0]
    for entry in rows:
        row=entry['data']
        try:
            if kind=='people':
                if not (row.get('first_name') or row.get('display_name')): raise ValueError('Falta el nombre de la persona')
                team=resolve(row.get('team_name'),entry); team_id=str(team['id'])
                person=client._person_role({'position':client._import_position(row.get('position')),**client._import_person_details(row)})
                if not client._coach_only(person): client._normalise_shirt_number(row.get('shirt_number'))
                if team_id not in groups:
                    if team_id not in roster_cache: roster_cache[team_id]=client.manager_list_team_rosters(team_id,competition_id)
                    if not roster_cache[team_id]: missing_rosters[team_id]=team['name']
                prepared.append({**entry,'team_id':team_id})
            else:
                home=resolve(row.get('home'),entry);away=resolve(row.get('away'),entry)
                if home['id']==away['id']: raise ValueError('Local y visitante deben ser distintos')
                when,known=schedule(row,tz_name)
                prepared.append({**entry,'payload':{'competition_id':competition_id,'home_team_id':home['id'],'away_team_id':away['id'],'match_date':when,'time_confirmed':known,'scheduled_date':datetime.fromisoformat(when).astimezone(ZoneInfo(tz_name)).date().isoformat(),'venue':str(row.get('venue') or '').strip() or None}})
        except Exception as exc: errors.append(f"{entry['sheet']}, fila {entry['row']}: {exc}")
    if not rows: errors.append('El archivo no contiene filas importables')
    return {'kind':kind,'total_rows':len(rows),'importable_rows':len(prepared),'errors':errors,
            'missing_teams':list(missing_teams.values()),'missing_rosters':[{'team_id':k,'name':v} for k,v in missing_rosters.items()],
            'ready':bool(prepared) and not errors and not missing_rosters,
            'preview':[{'hoja':e['sheet'],'fila':e['row'],**e['data']} for e in rows[:30]],'_prepared':prepared}

def commit(client,kind,rows,competition_id,season_id,tz_name):
    with IMPORT_LOCK:
        plan=preview(client,kind,rows,competition_id,season_id,tz_name)
        if not plan['ready']: return {**{k:v for k,v in plan.items() if k!='_prepared'},'blocked':True}
        report={'totals':{'created':0,'updated':0,'skipped':0,'failed':0},'errors':[]}
        if kind=='people':
            groups=defaultdict(list)
            for entry in plan['_prepared']:groups[entry['team_id']].append(entry)
            for team_id,entries in groups.items():
                # One row per dataset preserves the original source row in error reports.
                result=client.manager_import_roster(team_id,competition_id,[{'sheet':f"{e['sheet']} · fila {e['row']}",'rows':[e['data']]} for e in entries])
                for k in report['totals']:report['totals'][k]+=result['totals'][k]
                report['errors'].extend(result['errors'])
        else:
            for entry in plan['_prepared']:
                try:
                    result=client.manager_import_fixture(entry['payload'])
                    report['totals']['created' if result['created'] else 'skipped']+=1
                except Exception as exc:
                    report['totals']['failed']+=1;report['errors'].append(f"{entry['sheet']}, fila {entry['row']}: {exc}")
        return report
