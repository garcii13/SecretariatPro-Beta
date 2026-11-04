"""Desktop-managed federation connections. Private per-installation encrypted store.

No credentials in API responses, Git, logs or browser storage. Metadata and secrets
share the existing per-user data directory; its encryption key must be backed up
with this store. This does not protect against a compromised OS user account.
"""
from __future__ import annotations
import base64
import json
import os
import sqlite3
import time
import uuid
import urllib.request
from pathlib import Path
from cryptography.fernet import Fernet
from .client import checked_url, NoRedirect, SCHEMA

def directory():
    from .federation import cache_path
    return cache_path().parent

def cipher():
    root=directory();root.mkdir(parents=True,exist_ok=True,mode=0o700)
    path=root/'connection-settings.key'
    try:
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write(Fernet.generate_key())
    except FileExistsError:pass
    return Fernet(path.read_bytes())

def database():
    root=directory();root.mkdir(parents=True,exist_ok=True,mode=0o700)
    path=root/'connection-settings.sqlite'
    db=sqlite3.connect(path,timeout=10);os.chmod(path,0o600)
    db.executescript('''
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS profiles(id TEXT PRIMARY KEY,workspace TEXT,config BLOB,enabled INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS pending(id TEXT PRIMARY KEY,workspace TEXT,user_id TEXT,state BLOB,expires REAL);
    ''');return db

def stored(workspace,include_disabled=False):
    if not (directory()/'connection-settings.sqlite').exists():return []
    db=database()
    try:
        rows=db.execute('SELECT config,enabled FROM profiles WHERE workspace=?'+('' if include_disabled else ' AND enabled=1'),(str(workspace),)).fetchall()
        if not rows:return []
        key=cipher();return [{**json.loads(key.decrypt(row[0])), 'enabled':bool(row[1]),'managed':True} for row in rows]
    finally:db.close()

def secret(config):
    return str(config.get('storedSecret') or os.getenv(config.get('secretEnv',''),'') or '')

def read_code(code):
    if not isinstance(code,str) or len(code)>4096 or not code.strip().startswith('SX1.'):
        raise ValueError('Pega la invitación que te ha entregado tu federación.')
    try:
        raw=code.strip()[4:];data=json.loads(base64.urlsafe_b64decode(raw+'='*(-len(raw)%4)))
        if data.get('v')!=1 or len(data.get('token',''))!=43:raise ValueError()
        return {'url':checked_url(data['url']),'token':data['token']}
    except Exception:raise ValueError('La invitación no es válida. Copia el código completo.') from None

def remote(base,path,payload):
    req=urllib.request.Request(checked_url(base)+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.build_opener(NoRedirect).open(req,timeout=8) as res:
            raw=res.read(1024*1024+1)
            if len(raw)>1024*1024:raise ValueError()
            return json.loads(raw)
    except Exception:raise ValueError('No se pudo verificar la invitación. Comprueba la conexión o solicita una nueva a tu federación.') from None

def inspect(client,code):
    client._require_competition_manager()
    workspace=str(client._active_workspace_id());user=str(client.user_id)
    request=read_code(code);info=remote(request['url'],'/api/exchange/v1/invitations/inspect',{'token':request['token']})
    if info.get('schema')!=SCHEMA or not info.get('namespace') or not info.get('competitions'):
        raise ValueError('La federación no ofrece una conexión compatible o no ha autorizado competiciones.')
    competitions=info['competitions']
    if not isinstance(competitions,list) or len(competitions)>100 or any(not isinstance(c,dict) or not isinstance(c.get('id'),str) or not isinstance(c.get('name'),str) for c in competitions):raise ValueError('La lista de competiciones no es válida.')
    ticket=str(uuid.uuid4());state={**request,'info':info,'redemptionId':str(uuid.uuid4())}
    if str(client._active_workspace_id())!=workspace or str(client.user_id)!=user:raise ValueError('El espacio de trabajo cambió. Verifica de nuevo la invitación.')
    db=database()
    try:
        with db:
            db.execute('DELETE FROM pending WHERE expires<?',(time.time(),))
            db.execute('INSERT INTO pending VALUES(?,?,?,?,?)',(ticket,workspace,user,cipher().encrypt(json.dumps(state).encode()),time.time()+900))
    finally:db.close()
    return {'ticketId':ticket,'name':str(info.get('name') or info['namespace']),'namespace':info['namespace'],'competitions':[{'id':c['id'],'name':c['name'],'season':str(c.get('season') or '')} for c in competitions],'canCapture':'captures:write' in info.get('scopes',[])}

def finish(client,ticket_id,competition_id,capture=True,auto_import=False):
    client._require_competition_manager();workspace=str(client._active_workspace_id());db=database()
    try:
        row=db.execute('SELECT state FROM pending WHERE id=? AND workspace=? AND user_id=? AND expires>?',(ticket_id,workspace,str(client.user_id),time.time())).fetchone()
        if not row:raise ValueError('La verificación ha caducado. Pega de nuevo la invitación.')
        state=json.loads(cipher().decrypt(row[0]));info=state['info']
        if competition_id not in {c['id'] for c in info['competitions']}:raise ValueError('Elige una competición autorizada por tu federación.')
        if capture and 'captures:write' not in info.get('scopes',[]):raise PermissionError('La invitación solo permite consultar datos.')
        reply=remote(state['url'],'/api/exchange/v1/enroll',{'token':state['token'],'redemptionId':state['redemptionId']})
        if reply.get('schema')!=SCHEMA or reply.get('namespace')!=info['namespace'] or len(reply.get('secret',''))<32 or competition_id not in {c.get('id') for c in reply.get('competitions',[])}:raise ValueError('La respuesta de conexión no coincide con la federación verificada.')
        if not isinstance(reply.get('clientId'),str) or not reply['clientId'] or not isinstance(reply.get('sourceNamespace'),str) or not reply['sourceNamespace']:raise ValueError('La federación no devolvió una identidad de conexión válida.')
        if capture and 'captures:write' not in reply.get('scopes',[]):raise PermissionError('La federación no ha autorizado el envío de jugadas.')
        if str(client._active_workspace_id())!=workspace:raise ValueError('Vuelve al espacio donde verificaste la invitación para completar la conexión.')
        ident='gui-'+uuid.uuid5(uuid.NAMESPACE_URL,json.dumps([workspace,state['url'],reply['namespace'],reply['clientId'],competition_id])).hex
        config={'id':ident,'url':state['url'],'clientId':reply['clientId'],'sourceNamespace':reply['sourceNamespace'],'storedSecret':reply['secret'],'namespace':reply['namespace'],'competitionId':competition_id,'workspaceId':workspace,'name':info.get('name') or info['namespace'],'competitionName':next(c['name'] for c in info['competitions'] if c['id']==competition_id),'modules':['catalog','statistics']+(['captures'] if capture else []),'autoImport':bool(auto_import),'enabled':True}
        # Persist before any sporting download. A network failure preserves a
        # recoverable connection; it does not create a second remote credential.
        with db:
            db.execute('INSERT INTO profiles VALUES(?,?,?,1) ON CONFLICT(id) DO UPDATE SET config=excluded.config,enabled=1',(ident,workspace,cipher().encrypt(json.dumps(config).encode())))
            db.execute('DELETE FROM pending WHERE id=?',(ticket_id,))
        return {'ok':True,'id':ident,'name':config['name'],'competitionName':config['competitionName']}
    finally:db.close()

def set_enabled(client,ident,enabled):
    client._require_competition_manager();workspace=str(client._active_workspace_id())
    config=next((c for c in stored(workspace,True) if c['id']==ident),None)
    if not config:raise ValueError('Esta conexión no está guardada en este espacio.')
    if enabled:
        from .federation import connect
        exchange=connect(config)
        try:exchange.pull()
        finally:exchange.close()
    db=database()
    try:
        with db:db.execute('UPDATE profiles SET enabled=? WHERE id=? AND workspace=?',(int(enabled),ident,workspace))
    finally:db.close()
    return {'ok':True,'enabled':bool(enabled)}
