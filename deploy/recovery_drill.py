"""Quiesced local backup, isolated restore, outage/alert test and image rollback.

Run only after stopping host workers/load. Never restores over the source stack.
Private dumps, keys and filestore stay under ignored local/recovery.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import tarfile
import time
from uuid import uuid4

from dotenv import dotenv_values
import httpx
from psycopg import sql

from backend.monitor import Monitor, probe

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ['docker','compose','-f','compose.yaml','-f','compose.odoo.yaml','-f','compose.resources.yaml']
PROJECT = 'odoo-ops-drill'
APP_TABLES = ['actors','customers','proposals','approvals','operations','business_events','schema_migrations']
ODOO_TABLES = ['res_partner','product_product','product_template','crm_lead','ops_connection',
               'ops_operation','sale_order','sale_order_line','mail_activity','ir_attachment']


def command(args, *, env=None, data=None, output=None, timeout=120):
    kwargs = {'cwd':ROOT,'env':env,'input':data,'stderr':subprocess.PIPE,'timeout':timeout}
    if output:
        with Path(output).open('wb') as target:
            result = subprocess.run(args,stdout=target,**kwargs)
    else:
        result = subprocess.run(args,stdout=subprocess.PIPE,**kwargs)
    if result.returncode:
        raise RuntimeError('recovery_command_failed:'+args[0])
    return result.stdout or b''


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def query(compose,service,user,database,statement,env):
    return command(compose+['exec','-T',service,'psql','-X','-v','ON_ERROR_STOP=1','-U',user,'-d',database,'-At'],
                   env=env,data=statement.encode()).decode().strip()


def fingerprints(compose,service,user,database,tables,env):
    # Table names are fixed constants above, never caller input.
    return {table:query(compose,service,user,database,
        "SELECT count(*)||':'||md5(COALESCE(string_agg(md5(row_to_json(t)::text),'' ORDER BY md5(row_to_json(t)::text)),'')) FROM "+table+' t;',env)
        for table in tables}


def filestore_digest(archive):
    files = {}
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        for member in stream:
            if member.isfile():
                files[member.name] = hashlib.sha256(stream.extractfile(member).read()).hexdigest()
            elif not member.isdir():
                raise RuntimeError('unexpected_filestore_member')
    return {'files':len(files),'sha256':hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()}


def wait_ready(base,seconds=60):
    began = time.monotonic()
    while time.monotonic()-began < seconds:
        if probe(base):
            return time.monotonic()-began
        time.sleep(1)
    raise RuntimeError('readiness_recovery_timeout')


def verify_api(base,env,operation):
    with httpx.Client(base_url=base,trust_env=False,timeout=30) as client:
        response = client.post('/auth/login',json={'username':'operator.a','password':env['DEMO_PASSWORD']})
        response.raise_for_status()
        client.headers['Authorization'] = 'Bearer '+response.json()['access_token']
        try:
            catalog = client.get('/v1/catalog')
            catalog.raise_for_status()
            assert any(x['code']=='OPS-A-P1' for x in catalog.json()['items'])
            restored = client.get('/v1/operations/'+operation)
            restored.raise_for_status()
            assert restored.json()['id']==operation and restored.json()['status']=='verified'
            return {'operation_id':operation,'status':'verified','downstream_header_present':'X-Downstream-Duration-Ms' in catalog.headers}
        finally:
            client.post('/auth/logout')


def main():
    if os.environ.get('ODOO_LIVE_TESTS')!='synthetic-sandbox' or os.environ.get('RECOVERY_QUIESCE_CONFIRMED')!='yes':
        raise SystemExit('Require synthetic sandbox and stopped host producers: RECOVERY_QUIESCE_CONFIRMED=yes')
    env = {**os.environ,**{k:v for k,v in dotenv_values(ROOT/'.env').items() if v is not None}}
    connections = json.loads((ROOT/'local/odoo-config/connections.json').read_text())
    assert connections and all(x['database']=='odoo_ops_sandbox' and x['url']=='http://odoo:8069' for x in connections.values())
    for kind,args in [('container',['ps','-aq']),('volume',['volume','ls','-q']),('network',['network','ls','-q'])]:
        assert not command(['docker',*args,'--filter','label=com.docker.compose.project='+PROJECT]).strip(), 'Drill resources already exist'
    with socket.socket() as check:
        check.bind(('127.0.0.1',8021))
    run_id = str(uuid4())
    folder = ROOT/'local/recovery'/run_id
    folder.mkdir(parents=True)
    (folder/'config').mkdir()
    shutil.copy2(ROOT/'local/odoo-config/connections.json',folder/'config/connections.json')
    private_names = ['POSTGRES_PASSWORD','APP_DB_PASSWORD','ODOO_DB_PASSWORD','ODOO_ADMIN_PASSWORD','OPS_SIGNING_KEY','DEMO_PASSWORD']
    (folder/'private-config.json').write_text(json.dumps({k:env[k] for k in private_names}),encoding='utf-8')
    baseline = json.loads((ROOT/'local/phase8-baseline.json').read_text())
    cid = command(SOURCE+['ps','-q','api'],env=env).decode().strip()
    candidate = json.loads(command(['docker','inspect',cid]))[0]['Image']
    odoo_cid = command(SOURCE+['ps','-q','odoo'],env=env).decode().strip()
    postgres = 'postgres:17-bookworm@sha256:3645570cccdfa447589da9f57dd740faa29b30938e861289a5574b6ca6b03826'
    pg_health = {'test':['CMD-SHELL','pg_isready -U "$POSTGRES_USER"'],'interval':'2s','timeout':'3s','retries':30}
    label = {'ops.drill.run':run_id}
    services = {
        'db':{'image':postgres,'environment':{'POSTGRES_USER':'odoo_ops_owner','POSTGRES_DB':'odoo_ops_local','POSTGRES_PASSWORD':'${POSTGRES_PASSWORD}'},'volumes':['app-db:/var/lib/postgresql/data'],'healthcheck':pg_health,'mem_limit':'192m','labels':label},
        'odoo-db':{'image':postgres,'environment':{'POSTGRES_USER':'odoo','POSTGRES_DB':'odoo_ops_sandbox','POSTGRES_PASSWORD':'${ODOO_DB_PASSWORD}'},'volumes':['odoo-db:/var/lib/postgresql/data'],'healthcheck':pg_health,'mem_limit':'256m','labels':label},
        'odoo':{'image':baseline['odoo'],'environment':{k:'${'+k+'}' for k in ['ODOO_DB_PASSWORD','ODOO_ADMIN_PASSWORD','OPS_SIGNING_KEY']},
            'volumes':['filestore:/var/lib/odoo'], 'mem_limit':'768m','labels':label,
            'healthcheck':{'test':['CMD','python3','-c',"import urllib.request; urllib.request.urlopen('http://localhost:8069/web/health',timeout=5)"],'interval':'3s','timeout':'6s','retries':30}},
        'api':{'image':candidate,'environment':{'APP_ENV':'local','DATABASE_URL':'postgresql://odoo_ops_app:${APP_DB_PASSWORD}@db:5432/odoo_ops_local','ODOO_CONFIG_PATH':'/run/ops-config/connections.json','OPS_SIGNING_KEY':'${OPS_SIGNING_KEY}'},
            'volumes':[{'type':'bind','source':str(folder/'config'),'target':'/run/ops-config','read_only':True}],
            'ports':['127.0.0.1:8021:8000'],'read_only':True,'tmpfs':['/tmp'],'cap_drop':['ALL'],
            'security_opt':['no-new-privileges:true'],'mem_limit':'256m','labels':label},
    }
    config = {'name':PROJECT,'services':services,'volumes':{'app-db':{},'odoo-db':{},'filestore':{}}}
    compose = folder/'compose.json'
    def save_compose():
        compose.write_text(json.dumps(config,indent=2),encoding='utf-8')
    save_compose()
    lab = ['docker','compose','-p',PROJECT,'-f',str(compose)]
    owned, stopped = False, False
    report = {'run_id':run_id,'candidate_image':candidate,'rollback_image':baseline['api'],'passed':False}
    started = time.monotonic()
    try:
        stopped = True
        command(SOURCE+['stop','api','odoo'],env=env)
        print('Source API/Odoo quiesced; taking matching database and filestore snapshots.',flush=True)
        source_app = fingerprints(SOURCE,'db','odoo_ops_owner','odoo_ops_local',APP_TABLES,env)
        source_odoo = fingerprints(SOURCE,'odoo-db','odoo','odoo_ops_sandbox',ODOO_TABLES,env)
        operation = query(SOURCE,'db','odoo_ops_owner','odoo_ops_local',
            "SELECT id FROM operations WHERE tenant_id='00000000-0000-0000-0000-000000000001' AND status='verified' ORDER BY updated_at DESC LIMIT 1;",env)
        assert operation
        for service,user,database,name in [('db','odoo_ops_owner','odoo_ops_local','app.dump'),('odoo-db','odoo','odoo_ops_sandbox','odoo.dump')]:
            command(SOURCE+['exec','-T',service,'pg_dump','-U',user,'-d',database,'-Fc','--no-owner'],env=env,output=folder/name)
        command(['docker','cp',odoo_cid+':/var/lib/odoo/filestore','-'],output=folder/'filestore.tar')
        source_files = filestore_digest((folder/'filestore.tar').read_bytes())
        sqlite_copies = []
        for relative in ['local/worker/jobs.sqlite3','local/assistant-runs/tasks.sqlite3','local/phase8-worker/jobs.sqlite3','local/monitor/alerts.sqlite3']:
            path = ROOT/relative
            if path.exists():
                target = folder/(relative.replace('/','__'))
                with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as source, sqlite3.connect(target) as dest:
                    source.backup(dest)
                    assert dest.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
                sqlite_copies.append(target.name)
        backup_files = ['app.dump','odoo.dump','filestore.tar','config/connections.json','private-config.json',*sqlite_copies]
        hashes = {name:checksum(folder/name) for name in backup_files}
        (folder/'backup-manifest.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
        report['backup_seconds'] = time.monotonic()-started
        assert all(checksum(folder/name)==digest for name,digest in hashes.items())
        restore_start = time.monotonic()
        owned = True
        command(lab+['up','-d','--wait','--wait-timeout','90','db','odoo-db'],env=env)
        role = sql.SQL('CREATE ROLE odoo_ops_app LOGIN PASSWORD {};').format(sql.Literal(env['APP_DB_PASSWORD'])).as_string()
        query(lab,'db','odoo_ops_owner','odoo_ops_local',role,env)
        for service,user,database,name in [('db','odoo_ops_owner','odoo_ops_local','app.dump'),('odoo-db','odoo','odoo_ops_sandbox','odoo.dump')]:
            command(lab+['exec','-T',service,'pg_restore','-U',user,'-d',database,'--no-owner','--clean','--if-exists','--exit-on-error'],env=env,data=(folder/name).read_bytes())
        assert fingerprints(lab,'db','odoo_ops_owner','odoo_ops_local',APP_TABLES,env)==source_app
        assert fingerprints(lab,'odoo-db','odoo','odoo_ops_sandbox',ODOO_TABLES,env)==source_odoo
        command(lab+['create','odoo'],env=env)
        lab_odoo = command(lab+['ps','-aq','odoo'],env=env).decode().strip()
        command(['docker','cp','-a','-',lab_odoo+':/var/lib/odoo/'],data=(folder/'filestore.tar').read_bytes())
        restored_files = filestore_digest(command(['docker','cp',lab_odoo+':/var/lib/odoo/filestore','-']))
        assert restored_files==source_files
        # Restored auth sessions are deliberately invalidated, not made live again.
        query(lab,'db','odoo_ops_owner','odoo_ops_local','DELETE FROM sessions;',env)
        restored_state = folder/'restored-state'
        restored_state.mkdir()
        for name in sqlite_copies:
            shutil.copy2(folder/name,restored_state/name)
            assert checksum(restored_state/name)==hashes[name]
            with sqlite3.connect(restored_state/name) as db:
                assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        command(lab+['up','-d','--wait','--wait-timeout','90','odoo'],env=env)
        command(lab+['up','-d','api'],env=env)
        wait_ready('http://127.0.0.1:8021')
        report['restored_readback'] = verify_api('http://127.0.0.1:8021',env,operation)
        report['restore_seconds'] = time.monotonic()-restore_start
        assert report['restore_seconds']<=180
        print('Isolated database/filestore hashes and restored Odoo read-back verified.',flush=True)
        monitor = Monitor(folder/'alerts.sqlite3')
        command(lab+['stop','db'],env=env)
        for _ in range(2):
            assert not probe('http://127.0.0.1:8021')
            monitor.sample('api_readiness',False)
        firing = monitor.receive()
        assert len(firing)==1 and firing[0]['transition']=='firing'
        assert Monitor(folder/'alerts.sqlite3').receive()==[]
        recovery_start = time.monotonic()
        command(lab+['start','db'],env=env)
        wait_ready('http://127.0.0.1:8021')
        for _ in range(2):
            monitor.sample('api_readiness',probe('http://127.0.0.1:8021'))
        recovered = monitor.receive()
        assert len(recovered)==1 and recovered[0]['incident']==firing[0]['incident'] and recovered[0]['transition']=='recovered'
        report['database_recovery_seconds'] = time.monotonic()-recovery_start
        assert report['database_recovery_seconds']<=60
        report['alerts'] = {'firing_received':len(firing),'recovery_received':len(recovered),'duplicate_delivery':0,
                            'receiver':'local durable SQLite receiver; no external human paging'}
        services['api']['image'] = baseline['api']
        save_compose()
        command(lab+['up','-d','--no-deps','api'],env=env)
        wait_ready('http://127.0.0.1:8021')
        report['rollback_readback'] = verify_api('http://127.0.0.1:8021',env,operation)
        rollback_id = command(lab+['ps','-q','api'],env=env).decode().strip()
        assert json.loads(command(['docker','inspect',rollback_id]))[0]['Image']==baseline['api']
        services['api']['image'] = candidate
        save_compose()
        command(lab+['up','-d','--no-deps','api'],env=env)
        wait_ready('http://127.0.0.1:8021')
        report['rollforward_readback'] = verify_api('http://127.0.0.1:8021',env,operation)
        assert report['rollforward_readback']['downstream_header_present']
        forward_id = command(lab+['ps','-q','api'],env=env).decode().strip()
        assert json.loads(command(['docker','inspect',forward_id]))[0]['Image']==candidate
        report.update(passed=True,application_tables=source_app,odoo_tables=source_odoo,
                      filestore=source_files,sqlite_snapshots=len(sqlite_copies),backup_hashes=hashes)
        print('Database outage alert/recovery and rollback/rollforward verified.',flush=True)
    finally:
        try:
            if owned:
                ids = command(lab+['ps','-aq'],env=env).decode().splitlines()
                if ids:
                    values = json.loads(command(['docker','inspect',*ids]))
                    assert all(x['Config']['Labels'].get('ops.drill.run')==run_id for x in values)
                command(lab+['down','--volumes'],env=env)
        finally:
            try:
                if stopped:
                    command(SOURCE+['start','odoo','api'],env=env)
                    command(SOURCE+['up','-d','--no-deps','--wait','--wait-timeout','90','odoo','api'],env=env)
                    wait_ready('http://127.0.0.1:8020')
                    report['source_readback'] = verify_api('http://127.0.0.1:8020',env,operation)
                report['source_resumed'] = probe('http://127.0.0.1:8020')
            finally:
                report['total_seconds'] = time.monotonic()-started
                (ROOT/'local/phase8-recovery.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':report['passed'],'source_resumed':report['source_resumed'],'report':'local/phase8-recovery.json'}))


if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        raise SystemExit('recovery_drill_failed:'+type(exc).__name__+'; private evidence retained under local/recovery') from None
