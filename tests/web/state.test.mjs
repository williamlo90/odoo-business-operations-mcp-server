import {test} from 'node:test';
import assert from 'node:assert/strict';
import {escapeHTML,proposalState} from '../../backend/web/state.mjs';
const future='2099-01-01T00:00:00Z', past='2000-01-01T00:00:00Z';
test('source strings cannot become markup',()=>assert.equal(escapeHTML('<img src=x onerror="alert(1)">'), '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;'));
test('a saved operation takes precedence over proposal expiry',()=>{
  assert.equal(proposalState({expires_at:past,operation_status:'unknown'}),'unknown');
  assert.equal(proposalState({expires_at:past,approval_id:'a'}),'expired');
  assert.equal(proposalState({expires_at:future,approval_id:'a'}),'approved');
});
