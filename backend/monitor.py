"""Local durable incident spool and receiver; no external notification channel."""
import argparse
import json
from pathlib import Path
import sqlite3
import time
from urllib.parse import urlsplit
from uuid import uuid4

import httpx


def queue_metrics(path):
    uri = Path(path).resolve().as_uri()+'?mode=ro'
    with sqlite3.connect(uri, uri=True) as db:
        if db.execute('PRAGMA application_id').fetchone()[0] != 0x4F444F4F:
            raise ValueError('not_worker_queue')
        counts = dict(db.execute('SELECT state,count(*) FROM jobs GROUP BY state'))
        oldest = db.execute("SELECT min(created) FROM jobs WHERE state IN ('queued','retry_wait')").fetchone()[0]
    return {'counts': counts, 'oldest_wait_seconds': max(0, time.time()-oldest) if oldest else 0}


class Monitor:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            # Refuse an unrelated database, including a worker queue.
            app = db.execute('PRAGMA application_id').fetchone()[0]
            tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
            if app not in (0, 0x4F50534D) or app == 0 and tables:
                raise ValueError('not_monitor_database')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS health (service TEXT PRIMARY KEY, failures INTEGER,
                    successes INTEGER, incident TEXT);
                CREATE TABLE IF NOT EXISTS alerts (id TEXT PRIMARY KEY, service TEXT, incident TEXT,
                    transition TEXT, at REAL, received_at REAL);
                PRAGMA application_id=1330664269;
            ''')

    def sample(self, service, healthy, now=None):
        if service not in {'api_readiness','worker_backlog'} or type(healthy) is not bool:
            raise ValueError('invalid_observation')
        now = time.time() if now is None else now
        with sqlite3.connect(self.path) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT failures,successes,incident FROM health WHERE service=?',(service,)).fetchone()
            failures, successes, incident = row or (0,0,None)
            failures, successes = (0, successes+1) if healthy else (failures+1, 0)
            transition = None
            if failures >= 2 and incident is None:
                incident, transition = str(uuid4()), 'firing'
            elif successes >= 2 and incident:
                transition = 'recovered'
            if transition:
                db.execute('INSERT INTO alerts VALUES (?,?,?,?,?,NULL)',
                    (str(uuid4()),service,incident,transition,now))
            if transition == 'recovered':
                incident = None
            db.execute('INSERT OR REPLACE INTO health VALUES (?,?,?,?)',
                       (service,min(failures,2),min(successes,2),incident))
        return {'service':service,'healthy':healthy,'transition':transition}

    def receive(self, now=None):
        """Acknowledge a local receiver read; this is not human paging."""
        now = time.time() if now is None else now
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            db.execute('BEGIN IMMEDIATE')
            rows = [dict(row) for row in db.execute('SELECT * FROM alerts WHERE received_at IS NULL ORDER BY at,id')]
            db.executemany('UPDATE alerts SET received_at=? WHERE id=?',[(now,row['id']) for row in rows])
        return rows


def probe(base):
    url = urlsplit(base)
    if url.scheme != 'http' or url.hostname != '127.0.0.1' or url.port not in {8020,8021} or url.path or url.query or url.fragment or url.username:
        raise ValueError('fixed_local_api_required')
    try:
        with httpx.Client(timeout=3,trust_env=False,follow_redirects=False) as client:
            response = client.get(base+'/health/ready')
            return response.status_code == 200 and response.json().get('status') == 'ready'
    except (httpx.HTTPError, ValueError):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['check','receive'])
    parser.add_argument('--state',default='local/monitor/alerts.sqlite3')
    parser.add_argument('--api',default='http://127.0.0.1:8020')
    parser.add_argument('--queue')
    parser.add_argument('--samples',type=int,default=1)
    parser.add_argument('--interval',type=float,default=5)
    args = parser.parse_args()
    if not 1 <= args.samples <= 1000 or not 0.1 <= args.interval <= 3600:
        parser.error('invalid monitor limits')
    monitor = Monitor(args.state)
    if args.action == 'receive':
        print(json.dumps({'received':monitor.receive()}))
        return
    for index in range(args.samples):
        result = monitor.sample('api_readiness', probe(args.api))
        if args.queue:
            metric = queue_metrics(args.queue)
            healthy = metric['oldest_wait_seconds'] <= 300 and not any(metric['counts'].get(x,0) for x in ['review','dead'])
            result['worker'] = monitor.sample('worker_backlog', healthy)
            result['worker_metrics'] = metric
        print(json.dumps(result),flush=True)
        if index+1 < args.samples:
            time.sleep(args.interval)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, sqlite3.Error):
        raise SystemExit('monitor_unavailable_or_invalid_configuration') from None
