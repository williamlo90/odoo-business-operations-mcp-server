import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve, sep, basename } from 'node:path';
import { runAssistant } from '../dist/assistant.js';

test('TypeScript -> Python stdio -> authenticated HTTP -> sourced result and replay', async () => {
  const folder = await mkdtemp(join(tmpdir(), 'odoo-assistant-'));
  const calls = [];
  const server = http.createServer(async (req, res) => {
    for await (const _ of req) { /* consume bounded test request */ }
    calls.push(req.url);
    res.setHeader('Content-Type', 'application/json');
    if (req.url === '/auth/login') { res.end(JSON.stringify({access_token:'synthetic-session'})); return; }
    assert.equal(req.headers.authorization, 'Bearer synthetic-session');
    if (req.url === '/auth/logout') { res.writeHead(204); res.end(); return; }
    if (req.url === '/me') {
      res.end(JSON.stringify({id:'00000000-0000-0000-0000-000000000065', tenant_id:'00000000-0000-0000-0000-000000000001', role:'operator'})); return;
    }
    if (req.url.startsWith('/v1/customers?')) {
      res.end(JSON.stringify({items:[{id:7, name:'Synthetic customer', reference:'OPS-A-001', company_id:2, version:'v1'}], next_cursor:null, revision:'a'.repeat(64)})); return;
    }
    res.writeHead(404); res.end('{}');
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const before = {...process.env};
  process.env.API_URL = `http://127.0.0.1:${server.address().port}`;
  process.env.DEMO_PASSWORD = 'synthetic-password-for-test';
  process.env.ASSISTANT_STATE_DIR = folder;
  process.env.ASSISTANT_TRANSPORT = 'http';
  delete process.env.ASSISTANT_ENV_FILE;
  delete process.env.ASSISTANT_RATE_FILE;
  const packet = {task_id:'00000000-0000-0000-0000-000000000012', request:{request:{
    skill:'research_customer',customer_reference:'OPS-A-001',include_opportunities:false}}};
  try {
    const first = await runAssistant(packet);
    const second = await runAssistant(packet);
    assert.deepEqual(first, second);
    assert.equal(first.result.status, 'read');
    assert.equal(first.result.facts[0].source, 'odoo:res.partner:7');
    assert.equal(calls.filter(path => path.startsWith('/v1/customers')).length, 1);
    assert.equal(calls.filter(path => path === '/auth/logout').length, 2);
  } finally {
    for (const key of Object.keys(process.env)) if (!(key in before)) delete process.env[key];
    Object.assign(process.env, before);
    await new Promise(resolve => server.close(resolve));
    assert.ok(resolve(folder).startsWith(resolve(tmpdir())+sep) && basename(folder).startsWith('odoo-assistant-'));
    await rm(folder, {recursive:true, force:true});
  }
});

test('stdio boundary rejects malformed requests without exposing submitted secrets', async () => {
  await assert.rejects(runAssistant({request:{request:{skill:'execute',password:'private-input'}}}),
    error => error.message === 'assistant_invalid_response');
});
