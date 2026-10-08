"""Record actual reference CLI calls against the synthetic sandbox; no model spend."""
from collections import Counter
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import subprocess
import time
from uuid import uuid4

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def main():
    if os.environ.get('ODOO_LIVE_TESTS') != 'synthetic-sandbox':
        raise SystemExit('Set ODOO_LIVE_TESTS=synthetic-sandbox')
    config = json.loads((ROOT/'local/odoo-config/connections.json').read_text())
    assert all(x['database']=='odoo_ops_sandbox' and x['url']=='http://odoo:8069' for x in config.values())
    password = dotenv_values(ROOT/'.env')['DEMO_PASSWORD']
    env = {**os.environ,'API_URL':'http://127.0.0.1:8020','DEMO_PASSWORD':password}
    events = []
    def cli(title, role, args, expected=0):
        start = time.monotonic()
        result = subprocess.run(['node','client/dist/index.js',*args],cwd=ROOT,
            env={**env,'DEMO_USERNAME':role},capture_output=True,text=True,timeout=30)
        assert (result.returncode==0)==(expected==0), 'Unexpected demo command outcome'
        text = result.stdout.strip() if expected==0 else result.stderr.strip()
        assert password not in text
        value = json.loads(text) if expected==0 else text
        events.append({'title':title,'role':role,'command':'node client/dist/index.js '+' '.join(args),
                       'exit_code':result.returncode,'seconds':round(time.monotonic()-start,3),'output':value})
        return value
    customers = cli('Read scoped source records','operator.a',['customers'])
    duplicate = next(name for name,count in Counter(x['name'] for x in customers['items']).items() if count>1)
    denied = cli('Ambiguous name cannot select a customer','operator.a',['quote',duplicate,'OPS-A-P1:2'],1)
    assert 'unique customer reference' in denied
    proposal = cli('Prepare an exact quotation','operator.a',['quote','OPS-A-001','OPS-A-P1:2,OPS-A-P2:1'])
    assert float(proposal['preview']['total'])==250000
    denied = cli('Operator cannot approve their proposal','operator.a',['approve',proposal['id'],proposal['payload_hash']],1)
    assert '403' in denied
    approval = cli('Separate approver reviews and approves','approver.a',['approve',proposal['id'],proposal['payload_hash']])
    key = str(uuid4())
    args = ['execute',proposal['id'],approval['id'],key]
    operation = cli('Create the draft and verify Odoo read-back','operator.a',args)
    assert operation['status']=='verified' and float(operation['result']['record']['total'])==250000
    resumed = cli('Resume from saved operation ID after a caller restart','operator.a',['status',operation['id']])
    assert resumed['status']=='verified' and resumed['result']==operation['result']
    replay = cli('Replay the original execution key safely','operator.a',args)
    assert replay['id']==operation['id'] and replay['result']==operation['result']
    foreign = cli('Another tenant cannot see this operation','operator.b',['status',operation['id']],1)
    assert '404' in foreign
    sql = "SELECT (SELECT count(*) FROM ops_operation WHERE operation_id='"+operation['id']+"'),(SELECT count(*) FROM sale_order WHERE client_order_ref='ops:"+operation['id']+"');"
    # Only a validated UUID from the authenticated operation response enters SQL.
    from uuid import UUID
    assert str(UUID(operation['id']))==operation['id']
    counts = subprocess.check_output(['docker','compose','-f','compose.yaml','-f','compose.odoo.yaml','exec','-T','odoo-db',
        'psql','-U','odoo','-d','odoo_ops_sandbox','-At','-c',sql],cwd=ROOT,text=True).strip()
    assert counts=='1|1'
    report = {'recorded_at':datetime.now(timezone.utc).isoformat(),'application_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'scope':'Actual CLI recording; synthetic local data; separate test approver automated; no LLM call. Recovery is resume/replay, not injected network loss.',
        'passed':True,'operation_id':operation['id'],'ledger_count':1,'order_count':1,'events':events}
    target = ROOT/'docs/demo'; target.mkdir(exist_ok=True)
    (target/'recording.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    cards = ''.join('<section><h2>'+html.escape(e['title'])+'</h2><p>'+html.escape(e['role'])+' · '+str(e['seconds'])+' s · exit '+str(e['exit_code'])+'</p><pre>$ '+html.escape(e['command'])+'\n\n'+html.escape(json.dumps(e['output'],indent=2) if isinstance(e['output'],dict) else e['output'])+'</pre></section>' for e in events)
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Odoo operations — recorded CLI demo</title><style>body{font:16px system-ui;background:#111820;color:#e0e8ef;max-width:1000px;margin:40px auto;padding:0 24px}h1{font-size:36px}h2{font-size:21px;color:#83dfb5}p{color:#b0beca;line-height:1.6}section{margin:36px 0;border-top:1px solid #394651;padding-top:20px}pre{background:#080d12;padding:20px;overflow:auto;font-size:13px;line-height:1.5}a{color:#83dfb5}</style><h1>One approved draft. One verified outcome.</h1><p>Recorded reference CLI session · synthetic local Odoo · '+html.escape(report['recorded_at'])+'</p><p>'+html.escape(report['scope'])+'</p><p><b>PASS:</b> one operation ledger entry and one draft order. These are recorded outputs, not a live control panel.</p>'+cards+'</html>'
    (target/'index.html').write_text(page,encoding='utf-8',newline='\n')
    print(json.dumps({'passed':True,'events':len(events),'ledger_and_order_count':counts,'recording':'docs/demo/index.html'}))


if __name__=='__main__':
    main()
