"""Local orchestration journal. Business proposals remain in the domain database."""
import json
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import time
from uuid import uuid4

from backend.assistant.providers import AssistantError


class TaskJournal:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, actor TEXT NOT NULL, tenant TEXT NOT NULL,
                fingerprint TEXT NOT NULL, state TEXT NOT NULL, owner TEXT NOT NULL,
                lease_until REAL NOT NULL, decision TEXT, usage TEXT, result TEXT,
                error TEXT, updated REAL NOT NULL)''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=2)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def claim(self, task_id, identity, fingerprint, now=None):
        now = time.time() if now is None else now
        owner = str(uuid4())
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
            if row:
                if (row['actor'], row['tenant'], row['fingerprint']) != (identity['id'], identity['tenant_id'], fingerprint):
                    raise AssistantError('task_context_mismatch')
                if row['state'] == 'completed':
                    return {'cached': json.loads(row['result'])}
                if row['state'] in {'failed', 'review'}:
                    raise AssistantError('task_requires_review')
                if row['lease_until'] > now:
                    raise AssistantError('task_busy')
                if row['state'] != 'planned':
                    # A crash during dispatch cannot prove whether a proposal was committed.
                    db.execute("UPDATE tasks SET state='review',error='interrupted_task',updated=? WHERE id=?", (now, task_id))
                    db.commit()
                    raise AssistantError('task_requires_review')
                db.execute('UPDATE tasks SET owner=?,lease_until=?,updated=? WHERE id=?', (owner, now+300, now, task_id))
                return {'owner': owner, 'decision': json.loads(row['decision']), 'usage': json.loads(row['usage'])}
            db.execute('INSERT INTO tasks(id,actor,tenant,fingerprint,state,owner,lease_until,updated) VALUES (?,?,?,?,?,?,?,?)',
                       (task_id, identity['id'], identity['tenant_id'], fingerprint, 'planning', owner, now+300, now))
        return {'owner': owner}

    def checkpoint(self, task_id, owner, state, *, decision=None, usage=None, result=None, error=None):
        if state not in {'planned', 'dispatching', 'completed', 'failed', 'review'}:
            raise AssistantError('invalid_task_state')
        with self.connect() as db:
            changed = db.execute('''UPDATE tasks SET state=?,decision=COALESCE(?,decision),
                usage=COALESCE(?,usage),result=COALESCE(?,result),error=?,updated=?
                WHERE id=? AND owner=? AND state NOT IN ('completed','failed','review')''',
                (state, json.dumps(decision) if decision is not None else None,
                 json.dumps(usage) if usage is not None else None,
                 json.dumps(result) if result is not None else None, error, time.time(), task_id, owner)).rowcount
            if changed != 1:
                raise AssistantError('task_ownership_lost')
