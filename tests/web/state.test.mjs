import {test} from 'node:test';
import assert from 'node:assert/strict';
import {escapeHTML,proposalState,canExecute,executionKey} from '../../backend/web/state.mjs';
const future='2099-01-01T00:00:00Z', past='2000-01-01T00:00:00Z';
test('source strings cannot become markup',()=>assert.equal(escapeHTML('<img src=x onerror="alert(1)">'), '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;'));
test('a saved operation takes precedence over proposal expiry',()=>{
  assert.equal(proposalState({expires_at:past,operation_status:'unknown'}),'unknown');
  assert.equal(proposalState({expires_at:past,approval_id:'a'}),'expired');
  assert.equal(proposalState({expires_at:future,approval_id:'a'}),'approved');
});
test('only original operator with unexpired approval can execute a new operation',()=>{
  const d={proposal:{actor_id:'o'},approval:{expires_at:future},operation:null};
  assert.ok(canExecute({id:'o',role:'operator'},d));
  assert.ok(!canExecute({id:'b',role:'operator'},d));
  assert.ok(!canExecute({id:'o',role:'approver'},d));
  assert.ok(!canExecute({id:'o',role:'operator'},{...d,operation:{status:'unknown'}}));
  assert.ok(!canExecute({id:'o',role:'operator'},{...d,approval:{expires_at:past}}));
});
test('execution identity survives retries but is scoped to actor, tenant and proposal',()=>{
  const values=new Map(),storage={getItem:k=>values.get(k),setItem:(k,v)=>values.set(k,v)};
  let calls=0;const uuid=()=>`${String(++calls).padStart(8,'0')}-0000-4000-8000-000000000000`;
  const actor={id:'o',tenant_id:'a'}, first=executionKey(storage,actor,'p',uuid);
  assert.equal(executionKey(storage,actor,'p',uuid),first);
  assert.notEqual(executionKey(storage,{...actor,tenant_id:'b'},'p',uuid),first);
  assert.notEqual(executionKey(storage,actor,'p2',uuid),first);
  assert.equal(calls,3);
});
