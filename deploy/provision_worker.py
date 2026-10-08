"""Explicit per-tenant local worker profile and sandbox account provisioning."""
import argparse
import os
from pathlib import Path
import secrets
import subprocess

from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('tenant',choices=['a','b'])
args=parser.parse_args()
path=ROOT/'local'/'worker-profiles'/('company-'+args.tenant+'.env')
path.parent.mkdir(parents=True,exist_ok=True)
if not path.exists():
    tenant='00000000-0000-0000-0000-00000000000'+('1' if args.tenant=='a' else '2')
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        stream.write('API_URL=http://127.0.0.1:8020\nWORKER_USERNAME=automation.'+args.tenant+'\nWORKER_PASSWORD='+secrets.token_urlsafe(32)+'\nWORKER_TENANT_ID='+tenant+'\nWORKER_TRANSPORT=mcp\n')
profile=dotenv_values(path)
if profile.get('WORKER_USERNAME')!='automation.'+args.tenant or len(profile.get('WORKER_PASSWORD',''))<24:
    raise SystemExit('Invalid existing worker profile; preserved unchanged.')
env=os.environ.copy()
env.update(WORKER_PASSWORD=profile['WORKER_PASSWORD'],WORKER_TENANT_SUFFIX=args.tenant)
# Secret is passed through the process environment, never the command arguments.
subprocess.run(['docker','compose','-f','compose.yaml','-f','compose.odoo.yaml','run','--rm','--no-deps',
    '-e','WORKER_PASSWORD','-e','WORKER_TENANT_SUFFIX','migrate','python','-m','backend.provision_worker'],
    cwd=ROOT,env=env,check=True)
print('Private profile saved at '+str(path.relative_to(ROOT)))
