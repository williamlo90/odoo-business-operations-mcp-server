"""SQLite local job queue: scoped deduplication, leases, checkpoints and schedules."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
from uuid import uuid4

from backend.assistant.contracts import Clarify, Decision
from backend.assistant.providers import AssistantError

WRITE_SKILLS = {'prepare_quote', 'prepare_crm_activity'}


def serialized(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


class Queue:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            app_id=db.execute('PRAGMA application_id').fetchone()[0]
            version=db.execute('PRAGMA user_version').fetchone()[0]
            tables=db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
            if app_id not in {0,0x4F444F4F} or app_id==0 and tables or app_id==0x4F444F4F and version!=1:
                raise AssistantError('incompatible_queue_database')
            db.executescript('''
              CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, tenant TEXT NOT NULL, actor TEXT NOT NULL,
                event_key TEXT NOT NULL, fingerprint TEXT NOT NULL, request TEXT NOT NULL,
                skill TEXT NOT NULL, state TEXT NOT NULL, phase TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0, available REAL NOT NULL,
                owner TEXT, lease_until REAL, result TEXT, error TEXT,
                created REAL NOT NULL, updated REAL NOT NULL, UNIQUE(tenant,event_key));
              CREATE INDEX IF NOT EXISTS jobs_ready ON jobs(tenant,actor,state,available);
              CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, job TEXT NOT NULL,
                event TEXT NOT NULL, at REAL NOT NULL);
              CREATE TABLE IF NOT EXISTS schedules (
                id TEXT NOT NULL, tenant TEXT NOT NULL, actor TEXT NOT NULL,
                interval INTEGER NOT NULL, request TEXT NOT NULL,
                last_bucket INTEGER NOT NULL, active INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY(tenant,id));
            ''')
            db.execute('PRAGMA application_id=1329876815')
            db.execute('PRAGMA user_version=1')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=3)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def _enqueue(self, db, identity, event_key, decision, now):
        if isinstance(decision.request, Clarify) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,160}', event_key):
            raise AssistantError('invalid_job')
        if identity['role'] not in {'operator','approver','auditor'} or decision.request.skill in WRITE_SKILLS and identity['role'] != 'operator':
            raise AssistantError('job_permission_denied')
        raw = serialized(decision.model_dump())
        fingerprint = hashlib.sha256((identity['id']+raw).encode()).hexdigest()
        found = db.execute('SELECT * FROM jobs WHERE tenant=? AND event_key=?', (identity['tenant_id'], event_key)).fetchone()
        if found:
            if found['actor'] != identity['id'] or found['fingerprint'] != fingerprint:
                raise AssistantError('event_conflict')
            return found['id']
        ident = str(uuid4())
        db.execute('''INSERT INTO jobs(id,tenant,actor,event_key,fingerprint,request,skill,state,phase,available,created,updated)
            VALUES (?,?,?,?,?,?,?,'queued','queued',?,?,?)''',
            (ident,identity['tenant_id'],identity['id'],event_key,fingerprint,raw,decision.request.skill,now,now,now))
        db.execute('INSERT INTO events(job,event,at) VALUES (?,?,?)',(ident,'enqueued',now))
        return ident

    def enqueue(self, identity, event_key, decision: Decision, now=None):
        now = time.time() if now is None else now
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            return self._enqueue(db,identity,event_key,decision,now)

    def claim(self, identity, now=None):
        now = time.time() if now is None else now
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            expired = db.execute("SELECT * FROM jobs WHERE tenant=? AND actor=? AND state='running' AND lease_until<=?",
                                 (identity['tenant_id'],identity['id'],now)).fetchall()
            for row in expired:
                state = 'review' if row['phase']=='dispatching' and row['skill'] in WRITE_SKILLS else 'dead' if row['attempts']>=3 else 'retry_wait'
                db.execute('UPDATE jobs SET state=?,phase=?,error=?,available=?,updated=? WHERE id=?',
                           (state,state,'worker_interrupted',now,now,row['id']))
                db.execute('INSERT INTO events(job,event,at) VALUES (?,?,?)',(row['id'],'recovered_'+state,now))
            row = db.execute("""SELECT * FROM jobs WHERE tenant=? AND actor=? AND state IN ('queued','retry_wait')
                AND available<=? ORDER BY available,created,id LIMIT 1""",(identity['tenant_id'],identity['id'],now)).fetchone()
            if not row:
                return None
            owner = str(uuid4())
            db.execute("UPDATE jobs SET state='running',phase='claimed',owner=?,lease_until=?,attempts=attempts+1,updated=? WHERE id=?",
                       (owner,now+90,now,row['id']))
            db.execute('INSERT INTO events(job,event,at) VALUES (?,?,?)',(row['id'],'claimed',now))
            return dict(db.execute('SELECT * FROM jobs WHERE id=?',(row['id'],)).fetchone())

    def dispatch(self, job, now=None):
        now = time.time() if now is None else now
        with self.connect() as db:
            count = db.execute("UPDATE jobs SET phase='dispatching',updated=? WHERE id=? AND owner=? AND state='running' AND lease_until>?",
                               (now,job['id'],job['owner'],now)).rowcount
            if count != 1:
                raise AssistantError('job_lease_lost')
            db.execute('INSERT INTO events(job,event,at) VALUES (?,?,?)',(job['id'],'dispatching',now))

    def finish(self, job, state, *, result=None, error=None, now=None):
        now = time.time() if now is None else now
        if state not in {'completed','awaiting_approval','retry_wait','review','dead'}:
            raise AssistantError('invalid_job_state')
        available = now + min(300, 5 * 2**(job['attempts']-1)) if state=='retry_wait' else now
        with self.connect() as db:
            count = db.execute('''UPDATE jobs SET state=?,phase=?,available=?,result=?,error=?,updated=?
                WHERE id=? AND owner=? AND state='running' AND lease_until>?''',
                (state,state,available,serialized(result) if result is not None else None,error,now,
                 job['id'],job['owner'],now)).rowcount
            if count != 1:
                raise AssistantError('job_lease_lost')
            db.execute('INSERT INTO events(job,event,at) VALUES (?,?,?)',(job['id'],state,now))

    def inspect(self, identity, job_id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=? AND tenant=? AND actor=?',
                             (job_id,identity['tenant_id'],identity['id'])).fetchone()
            if not row:
                raise AssistantError('job_not_found')
            value = {key:row[key] for key in ('id','skill','state','phase','attempts','available','error','created','updated')}
            value['result'] = json.loads(row['result']) if row['result'] else None
            value['events'] = [dict(item) for item in db.execute('SELECT event,at FROM events WHERE job=? ORDER BY id',(job_id,))]
            return value

    def add_schedule(self, identity, name, interval, decision, now=None):
        now = time.time() if now is None else now
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}',name) or type(interval) is not int or not 60<=interval<=86400 or isinstance(decision.request,Clarify):
            raise AssistantError('invalid_schedule')
        if identity['role'] not in {'operator','approver','auditor'} or decision.request.skill in WRITE_SKILLS and identity['role'] != 'operator':
            raise AssistantError('job_permission_denied')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT * FROM schedules WHERE tenant=? AND id=?',(identity['tenant_id'],name)).fetchone()
            raw = serialized(decision.model_dump())
            if old:
                if (old['actor'],old['interval'],old['request']) != (identity['id'],interval,raw):
                    raise AssistantError('schedule_conflict')
                return
            count=db.execute('SELECT count(*) FROM schedules WHERE tenant=? AND actor=?',(identity['tenant_id'],identity['id'])).fetchone()[0]
            if count>=20:
                raise AssistantError('schedule_limit')
            db.execute('INSERT INTO schedules(id,tenant,actor,interval,request,last_bucket) VALUES (?,?,?,?,?,?)',
                       (name,identity['tenant_id'],identity['id'],interval,raw,int(now)//interval-1))

    def tick(self, identity, now=None):
        now = time.time() if now is None else now
        emitted=[]
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            for row in db.execute('SELECT * FROM schedules WHERE tenant=? AND actor=? AND active=1',(identity['tenant_id'],identity['id'])).fetchall():
                bucket=int(now)//row['interval']
                if bucket<=row['last_bucket']:
                    continue
                ident=self._enqueue(db,identity,f"schedule:{row['id']}:{bucket}",Decision.model_validate_json(row['request']),now)
                db.execute('UPDATE schedules SET last_bucket=? WHERE id=? AND tenant=?',(bucket,row['id'],identity['tenant_id']))
                emitted.append(ident)
        return emitted

    def disable_schedule(self, identity, name):
        with self.connect() as db:
            if db.execute('UPDATE schedules SET active=0 WHERE id=? AND tenant=? AND actor=?',
                          (name,identity['tenant_id'],identity['id'])).rowcount != 1:
                raise AssistantError('schedule_not_found')
