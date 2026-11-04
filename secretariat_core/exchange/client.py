"""Sports Exchange v1. Optional federation connector; no Supabase dependency.

One instance belongs to one worker. SQLite keeps namespaces, cursors and deliveries
separate from the application's event tables. No API secret is persisted here.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import sqlite3
import time
import uuid
import urllib.parse
import urllib.request
from pathlib import Path

SCHEMA = 'sports.exchange.v1'
PREFIX = '/api/exchange/v1'
FIELDS = {
    'competition': {'id','name','season','category','pointsWin','pointsDraw','pointsLoss'},
    'team': {'id','name','shortName','logo'},
    'roster': {'id','teamId','season','archived','players'},
    'match': {'id','competitionId','season','homeTeamId','awayTeamId','startsAt','venue','matchStatus','home','away','clock','period','reviewStatus','captureAllowed','lineup','events','keepers'},
}
REPORT_FIELDS={'lineup':{'teamId','playerId','name','number','position'},'events':{'id','teamId','type','seconds','period','sequence','timeBasis','sourceCreatedAt','playerId','assistantId','ownGoal','shootout','penaltyType'},'keepers':{'teamId','playerId','seconds','shots','saves'}}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('La integración no sigue redirecciones; revisa la URL base.')

def checked_url(base):
    p=urllib.parse.urlsplit(base)
    if p.username or p.password or p.query or p.fragment or p.path not in ('','/'):
        raise ValueError('La URL de la federación debe ser un origen sin credenciales ni ruta.')
    if not p.hostname or (p.scheme!='https' and not (p.scheme=='http' and p.hostname in ('127.0.0.1','localhost','::1'))):
        raise ValueError('Se requiere HTTPS, salvo loopback de desarrollo.')
    return base.rstrip('/')

def signed_headers(secret, client, method, path, raw=b'', delivery=None):
    stamp=str(int(time.time())); delivery=delivery or str(uuid.uuid4())
    message='\n'.join((stamp,delivery,method,path,hashlib.sha256(raw).hexdigest()))
    return {'Content-Type':'application/json','X-Exchange-Client':client,'X-Exchange-Timestamp':stamp,
            'X-Exchange-Delivery':delivery,'X-Exchange-Signature':hmac.new(secret.encode(),message.encode(),hashlib.sha256).hexdigest()}

class ExchangeClient:
    def __init__(self, base_url, client_id, secret, namespace, competition_id, cache_path, source_namespace=None):
        self.base=checked_url(base_url)
        if len(secret)<32 or not namespace or not competition_id or not client_id:
            raise ValueError('Configura identidad, secreto de al menos 32 caracteres, federación y competición.')
        self.client_id,self.secret,self.namespace,self.competition=client_id,secret,namespace,competition_id
        self.source_namespace=source_namespace or 'urn:exchange-client:'+client_id
        path=Path(cache_path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.db=sqlite3.connect(path,timeout=10)
        os.chmod(path,0o600)
        self.db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS meta(scope TEXT PRIMARY KEY,cursor TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS entities(scope TEXT,kind TEXT,id TEXT,revision INTEGER,payload TEXT,PRIMARY KEY(scope,kind,id));
        CREATE TABLE IF NOT EXISTS outbox(delivery TEXT PRIMARY KEY,scope TEXT,match_id TEXT,revision INTEGER,body TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS captures(scope TEXT,match_id TEXT,revision INTEGER,digest TEXT,PRIMARY KEY(scope,match_id));
        CREATE TABLE IF NOT EXISTS receipts(delivery TEXT PRIMARY KEY,scope TEXT,body TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS bindings(scope TEXT,kind TEXT,external_id TEXT,local_id TEXT,PRIMARY KEY(scope,kind,external_id),UNIQUE(scope,kind,local_id));
        CREATE TABLE IF NOT EXISTS sync_status(scope TEXT PRIMARY KEY,last_pull REAL);
        ''');self.db.commit()
        self.scope=json.dumps([self.base,client_id,namespace,competition_id],separators=(',',':'))
        self.opener=urllib.request.build_opener(NoRedirect)

    def close(self): self.db.close()
    def request(self,method,path,payload=None,delivery=None):
        raw=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode() if payload is not None else b''
        req=urllib.request.Request(self.base+path,data=raw if method=='POST' else None,
            headers=signed_headers(self.secret,self.client_id,method,path,raw,delivery),method=method)
        try:
            with self.opener.open(req,timeout=8) as res:
                raw=res.read(8*1024*1024+1)
                if len(raw)>8*1024*1024:raise ValueError('Respuesta de integración demasiado grande.')
                return json.loads(raw)
        except Exception as exc:
            raise RuntimeError('La federación no está disponible o rechazó la operación; se conserva la cola.') from None

    def _check(self,data):
        if data.get('schema')!=SCHEMA or data.get('namespace')!=self.namespace or data.get('competitionId')!=self.competition:
            raise ValueError('Contrato, federación o competición incompatibles.')

    def _store(self,row):
        kind=row['kind'];data=row['data'];ident=str(row['id']);rev=int(row['revision'])
        if kind not in FIELDS or set(data)-FIELDS[kind] or str(data.get('id'))!=ident or rev<1:
            raise ValueError('Entidad deportiva no compatible.')
        if kind=='match' and data.get('competitionId')!=self.competition:
            raise ValueError('Partido de otra competición.')
        if kind=='roster':
            if any(set(p)-{'id','name','number','position'} for p in data.get('players',[])):
                raise ValueError('El roster contiene campos ajenos al contrato deportivo.')
        if kind=='match':
            for group,allowed in REPORT_FIELDS.items():
                if any(set(row)-allowed for row in data.get(group,[])):raise ValueError('El acta contiene campos ajenos al contrato deportivo.')
            prior=self.db.execute('SELECT payload,revision FROM entities WHERE scope=? AND kind=? AND id=?',(self.scope,kind,ident)).fetchone()
            if prior and rev>=prior[1] and not json.loads(prior[0]).get('captureAllowed') and data.get('captureAllowed'):
                # A reopened federation review requires re-publishing the latest
                # local snapshot even if no new goal has occurred in the desk.
                self.db.execute("UPDATE captures SET digest='' WHERE scope=? AND match_id=?",(self.scope,ident))
        self.db.execute('''INSERT INTO entities VALUES(?,?,?,?,?) ON CONFLICT(scope,kind,id)
            DO UPDATE SET revision=excluded.revision,payload=excluded.payload WHERE excluded.revision>=entities.revision''',
            (self.scope,kind,ident,rev,json.dumps(data,ensure_ascii=False)))

    def bootstrap(self):
        data=self.request('GET',PREFIX+'/snapshot?'+urllib.parse.urlencode({'competition':self.competition}))
        return self.import_snapshot(data)

    def import_snapshot(self,data):
        """Same validated sporting contract for an offline JSON handoff."""
        self._check(data)
        with self.db:
            self.db.execute('DELETE FROM entities WHERE scope=?',(self.scope,))
            for row in data['entities']:self._store(row)
            self.db.execute('INSERT INTO meta VALUES(?,?) ON CONFLICT(scope) DO UPDATE SET cursor=excluded.cursor',(self.scope,str(data['nextCursor'])))
            # Restore the producer's revision after a cache rebuild/new workstation.
            # The server returns only this authenticated connection's checkpoints.
            for head in data.get('captureCheckpoints',[]):
                revision=int(head['revision'])
                if revision<1 or revision>9007199254740991:raise ValueError('Checkpoint fuera de rango.')
                self.db.execute("INSERT INTO captures VALUES(?,?,?,'') ON CONFLICT(scope,match_id) DO UPDATE SET revision=excluded.revision,digest='' WHERE excluded.revision>captures.revision",(self.scope,head['matchId'],revision))
            self.db.execute('INSERT OR REPLACE INTO sync_status VALUES(?,?)',(self.scope,time.time()))
        return len(data['entities'])

    def pull(self):
        cursor=self.db.execute('SELECT cursor FROM meta WHERE scope=?',(self.scope,)).fetchone()
        if not cursor:return self.bootstrap()
        count=0;after=cursor[0]
        for _ in range(100):
            data=self.request('GET',PREFIX+'/changes?'+urllib.parse.urlencode({'competition':self.competition,'after':after}));self._check(data)
            with self.db:
                for row in data['changes']:self._store(row);count+=1
                next_cursor=str(data['nextCursor'])
                if data.get('hasMore') and next_cursor==after:raise ValueError('Cursor sin progreso.')
                after=next_cursor;self.db.execute('UPDATE meta SET cursor=? WHERE scope=?',(after,self.scope))
                self.db.execute('INSERT OR REPLACE INTO sync_status VALUES(?,?)',(self.scope,time.time()))
            if not data.get('hasMore'):return count
        raise ValueError('Demasiadas páginas de cambios en una consulta.')

    def snapshot(self,kind):
        return [json.loads(r[0]) for r in self.db.execute('SELECT payload FROM entities WHERE scope=? AND kind=? ORDER BY id',(self.scope,kind))]

    def bind(self,kind,external_id,local_id):
        with self.db:self.db.execute('INSERT INTO bindings VALUES(?,?,?,?) ON CONFLICT(scope,kind,external_id) DO UPDATE SET local_id=excluded.local_id',(self.scope,kind,external_id,local_id))
    def mapped(self,kind,ident,reverse=False):
        a,b=('local_id','external_id') if reverse else ('external_id','local_id')
        row=self.db.execute(f'SELECT {b} FROM bindings WHERE scope=? AND kind=? AND {a}=?',(self.scope,kind,str(ident))).fetchone()
        if not row:raise ValueError('Falta vincular la identidad deportiva con su federación.')
        return row[0]

    def enqueue(self,match_id,data):
        # Content-based enqueueing plus persistent monotonic revisions, across app restarts.
        body=json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(',',':'))
        digest=hashlib.sha256(body.encode()).hexdigest()
        self.db.execute('BEGIN IMMEDIATE')
        try:
            prior=self.db.execute('SELECT revision,digest FROM captures WHERE scope=? AND match_id=?',(self.scope,match_id)).fetchone()
            if prior and prior[1]==digest:self.db.rollback();return None
            revision=(prior[0] if prior else 0)+1;delivery=str(uuid.uuid4())
            payload={'schema':SCHEMA,'namespace':self.namespace,'matchId':match_id,'revision':revision,'match':data}
            payload={'specversion':'1.0','id':delivery,'source':self.source_namespace,'type':'sports.match.capture.v1','subject':match_id,'datacontenttype':'application/json','data':payload}
            self.db.execute('INSERT INTO captures VALUES(?,?,?,?) ON CONFLICT(scope,match_id) DO UPDATE SET revision=excluded.revision,digest=excluded.digest',(self.scope,match_id,revision,digest))
            self.db.execute('INSERT INTO outbox VALUES(?,?,?,?,?,?)',(delivery,self.scope,match_id,revision,json.dumps(payload,ensure_ascii=False),time.time()))
            self.db.commit();return delivery
        except Exception:self.db.rollback();raise

    def flush(self):
        receipts=[]
        for delivery,body in self.db.execute('SELECT delivery,body FROM outbox WHERE scope=? ORDER BY created,revision LIMIT 100',(self.scope,)).fetchall():
            receipt=self.request('POST',PREFIX+'/captures',json.loads(body),delivery)
            if receipt.get('ok') is not True:raise ValueError('La federación no confirmó la entrega.')
            with self.db:
                self.db.execute('INSERT OR REPLACE INTO receipts VALUES(?,?,?,?)',(delivery,self.scope,json.dumps(receipt),time.time()))
                self.db.execute('DELETE FROM outbox WHERE delivery=?',(delivery,))
            receipts.append(receipt)
        return receipts

    def status(self):
        row=self.db.execute('SELECT body FROM receipts WHERE scope=? ORDER BY created DESC LIMIT 1',(self.scope,)).fetchone()
        synced=self.db.execute('SELECT last_pull FROM sync_status WHERE scope=?',(self.scope,)).fetchone()
        return {'namespace':self.namespace,'competitionId':self.competition,'cached':self.db.execute('SELECT count(*) FROM entities WHERE scope=?',(self.scope,)).fetchone()[0],
                'pending':self.db.execute('SELECT count(*) FROM outbox WHERE scope=?',(self.scope,)).fetchone()[0], 'lastReceipt':json.loads(row[0]) if row else None,'lastSyncedAt':synced[0] if synced else None}
