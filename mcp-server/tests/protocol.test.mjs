import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { readFile, writeFile, mkdtemp, rm } from 'node:fs/promises';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';
import { join, resolve, sep, basename } from 'node:path';
import { connectMcp } from '../dist/connection.js';
import { runAssistant } from '../../client/dist/assistant.js';

const proposal = JSON.parse(await readFile(new URL('../../tests/assistant/fixtures/proposal.json',import.meta.url),'utf8'));
const operation = JSON.parse(await readFile(new URL('../../tests/assistant/fixtures/operation.json',import.meta.url),'utf8'));
const uuid='00000000-0000-0000-0000-000000000020';
const unwrap = result => result.structuredContent ?? JSON.parse(result.content[0].text);

async function fixture(extraEnv={}) {
  const state={role:'operator',auth:true,stale:false,foreign:false,delay:0,effects:0,unknown:false,badReceipt:false,calls:[]};
  const server=http.createServer(async(req,res)=>{
    let raw=''; for await(const chunk of req)raw+=chunk;
    const body=raw ? JSON.parse(raw) : null;
    const path=new URL(req.url,'http://localhost').pathname;
    state.calls.push(path);
    res.setHeader('Content-Type','application/json');
    const send=(status,data)=>{if(!res.destroyed){res.writeHead(status);res.end(JSON.stringify(data));}};
    if(path==='/auth/login')return send(200,{access_token:'synthetic-token'});
    if(path==='/auth/logout'){res.writeHead(204);res.end();return;}
    if(!state.auth)return send(401,{error:'invalid_session',private:'secret-do-not-echo'});
    if(path==='/me')return send(200,{id:proposal.actor_id,tenant_id:proposal.tenant_id,role:state.role,username:'private-user'});
    if(path==='/v1/customers'){
      if(state.delay)await new Promise(resolve=>setTimeout(resolve,state.delay));
      return send(200,{items:[{id:7,name:'Synthetic',reference:'OPS-A-001',company_id:2,source:'odoo:res.partner',version:'v1'}],next_cursor:null,revision:'a'.repeat(64),ambiguous:false});
    }
    if(path==='/v1/catalog')return send(200,{items:[{id:1,code:'OPS-A-P1',name:'Service 1',unit_price:'100000'},{id:2,code:'OPS-A-P2',name:'Service 2',unit_price:'50000'}],currency:'IDR',pricing_policy:'list-price-no-tax-v1'});
    if(path==='/v1/quotes/prepare')return send(201,proposal);
    if(path===`/v1/proposals/${proposal.id}`)return send(200,state.foreign ? {...proposal,tenant_id:uuid}:proposal);
    if(path.endsWith('/execute')){
      if(state.stale)return send(409,{error:'stale_proposal'});
      if(body.approval_id!==operation.approval_id)return send(409,{error:'approval_expired'});
      if(!state.effects)state.effects=1;
      if(state.unknown)return send(503,{error:'database_unavailable'});
      return send(200,{...operation,idempotency_key:body.idempotency_key});
    }
    if(path.startsWith('/v1/operations/'))return send(200,state.badReceipt ? {...operation,result:null}:operation);
    return send(404,{error:'not_found'});
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const base=`http://127.0.0.1:${server.address().port}`;
  let client;
  try { ({client}=await connectMcp({API_URL:base,ODOO_OPS_TOKEN:'synthetic-token',...extraEnv})); }
  catch(error){await new Promise(resolve=>server.close(resolve));throw error;}
  return {state,base,client,close:async()=>{await client.close();await new Promise(resolve=>server.close(resolve));}};
}

test('real MCP initialize, tool schemas, preparation and verified idempotent execution',async()=>{
  const f=await fixture();
  try{
    assert.equal(f.client.getNegotiatedProtocolVersion(),'2026-07-28');
    const listed=await f.client.listTools();
    assert.equal(listed.tools.length,10);
    assert.ok(!listed.tools.some(t=>t.name.includes('approve') && t.name!=='odoo.execute_approved'));
    for(const tool of listed.tools)assert.equal(tool.inputSchema.additionalProperties,false);
    const prepared=unwrap(await f.client.callTool({name:'odoo.quote_prepare',arguments:proposal.payload}));
    assert.equal(prepared.data.id,proposal.id);
    const args={proposal_id:proposal.id,approval_id:operation.approval_id,idempotency_key:operation.idempotency_key};
    const outputs=await Promise.all([f.client.callTool({name:'odoo.execute_approved',arguments:args}),f.client.callTool({name:'odoo.execute_approved',arguments:args})]);
    assert.ok(outputs.every(result=>unwrap(result).data.status==='verified'));
    assert.equal(f.state.effects,1);
    const checked=unwrap(await f.client.callTool({name:'odoo.operation_status',arguments:{operation_id:operation.id}}));
    assert.equal(checked.data.result.record.total,'250000.0');
  }finally{await f.close();}
});

test('schema injection and wrong role cannot dispatch a business write',async()=>{
  const f=await fixture();
  try{
    const invalid=await f.client.callTool({name:'odoo.quote_prepare',arguments:{...proposal.payload,tenant_id:uuid,url:'http://evil.test'}});
    assert.equal(invalid.isError,true);
    assert.equal(f.state.calls.length,0);
    f.state.role='auditor';
    const denied=unwrap(await f.client.callTool({name:'odoo.quote_prepare',arguments:proposal.payload}));
    assert.equal(denied.error,'role_not_permitted');
    assert.ok(!f.state.calls.includes('/v1/quotes/prepare'));
  }finally{await f.close();}
});

test('expired identity, stale approval, and cross-tenant proposal are rejected',async()=>{
  const f=await fixture();
  try{
    f.state.auth=false;
    const denied=await f.client.callTool({name:'odoo.identity',arguments:{}});
    assert.equal(unwrap(denied).error,'invalid_session');
    assert.ok(!JSON.stringify(denied).includes('secret-do-not-echo'));
    f.state.auth=true;f.state.stale=true;
    const args={proposal_id:proposal.id,approval_id:operation.approval_id,idempotency_key:operation.idempotency_key};
    assert.equal(unwrap(await f.client.callTool({name:'odoo.execute_approved',arguments:args})).error,'stale_proposal');
    f.state.stale=false;f.state.foreign=true;
    assert.equal(unwrap(await f.client.callTool({name:'odoo.execute_approved',arguments:args})).error,'access_denied');
    assert.equal(f.state.effects,0);
  }finally{await f.close();}
});

test('lost write outcome stays unknown and malformed receipt cannot claim success',async()=>{
  const f=await fixture();
  try{
    f.state.unknown=true;
    const result=unwrap(await f.client.callTool({name:'odoo.execute_approved',arguments:{proposal_id:proposal.id,approval_id:operation.approval_id,idempotency_key:operation.idempotency_key}}));
    assert.equal(result.error,'write_outcome_unknown');assert.equal(f.state.effects,1);
    assert.equal(unwrap(await f.client.callTool({name:'odoo.operation_status',arguments:{operation_id:operation.id}})).data.status,'verified');
    f.state.badReceipt=true;
    assert.equal(unwrap(await f.client.callTool({name:'odoo.operation_status',arguments:{operation_id:operation.id}})).error,'invalid_verified_receipt');
  }finally{await f.close();}
});

test('bounded downstream timeout and concurrent request limit',async()=>{
  const f=await fixture({MCP_DOMAIN_TIMEOUT_MS:'100'});
  try{
    f.state.delay=300;
    const results=await Promise.all(Array.from({length:5},()=>f.client.callTool({name:'odoo.customer_search',arguments:{query:'OPS-A-001'}})));
    assert.ok(results.some(result=>unwrap(result).error==='request_limit'));
    assert.ok(results.some(result=>unwrap(result).error==='domain_unavailable'));
  }finally{await f.close();}
});

test('MCP cancellation aborts waiting and connection remains usable',async()=>{
  const f=await fixture();
  try{
    f.state.delay=200;
    const controller=new AbortController();
    const pending=f.client.callTool({name:'odoo.customer_search',arguments:{query:'OPS-A-001'}},{signal:controller.signal});
    setTimeout(()=>controller.abort(),25);
    await assert.rejects(pending);
    const next=unwrap(await f.client.callTool({name:'odoo.identity',arguments:{}}));
    assert.equal(next.data.role,'operator');
  }finally{await f.close();}
});

test('TypeScript assistant -> Python skills -> TypeScript MCP -> domain fixture',async()=>{
  const f=await fixture();const directory=await mkdtemp(join(tmpdir(),'odoo-mcp-'));
  const before={...process.env};
  Object.assign(process.env,{API_URL:f.base,DEMO_PASSWORD:'synthetic-test-password',ASSISTANT_TRANSPORT:'mcp',ASSISTANT_STATE_DIR:directory});
  delete process.env.ASSISTANT_ENV_FILE;delete process.env.ASSISTANT_RATE_FILE;
  try{
    const result=await runAssistant({request:{request:{skill:'prepare_quote',customer_reference:'OPS-A-001',items:[{product_code:'OPS-A-P1',quantity:2},{product_code:'OPS-A-P2',quantity:1}]}}});
    assert.equal(result.result.status,'awaiting_approval');
    assert.equal(result.result.proposal.preview.total,'250000.0');
    assert.equal(f.state.effects,0);
  }finally{
    for(const key of Object.keys(process.env))if(!(key in before))delete process.env[key];
    Object.assign(process.env,before);await f.close();
    assert.ok(resolve(directory).startsWith(resolve(tmpdir())+sep) && basename(directory).startsWith('odoo-mcp-'));
    await rm(directory,{recursive:true,force:true});
  }
});

test('separate worker CLI processes persist one proposal job through MCP and replay',async()=>{
  const f=await fixture();const directory=await mkdtemp(join(tmpdir(),'odoo-worker-'));
  const root=fileURLToPath(new URL('../../',import.meta.url));
  const python=join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
  const queue=join(directory,'jobs.sqlite3');const requestFile=join(directory,'request.json');
  await writeFile(requestFile,JSON.stringify({request:{skill:'prepare_quote',customer_reference:'OPS-A-001',
    items:[{product_code:'OPS-A-P1',quantity:2},{product_code:'OPS-A-P2',quantity:1}]}}));
  const env={...process.env,API_URL:f.base,WORKER_USERNAME:'operator.a',WORKER_PASSWORD:'synthetic-worker-password',
    WORKER_TENANT_ID:proposal.tenant_id,WORKER_TRANSPORT:'mcp'};
  const command=async args=>JSON.parse((await promisify(execFile)(python,['-m','backend.worker','--queue',queue,...args],
    {cwd:root,env,windowsHide:true,timeout:15000,maxBuffer:262144})).stdout);
  try{
    const {job_id}=await command(['enqueue','worker-event',requestFile]);
    assert.equal((await command(['enqueue','worker-event',requestFile])).job_id,job_id);
    assert.equal((await command(['run-once'])).state,'awaiting_approval');
    assert.equal((await command(['inspect',job_id])).result.proposal.id,proposal.id);
    assert.equal((await command(['run-once'])).state,'idle');
    assert.equal(f.state.calls.filter(path=>path==='/v1/quotes/prepare').length,1);
    assert.equal(f.state.effects,0);
  }finally{
    await f.close();
    assert.ok(resolve(directory).startsWith(resolve(tmpdir())+sep) && basename(directory).startsWith('odoo-worker-'));
    await rm(directory,{recursive:true,force:true});
  }
});
