export const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const expired = value => !value || !Number.isFinite(Date.parse(value)) || Date.parse(value) <= Date.now();
export function proposalState(row) {
  return row.operation_status || row.operation?.status || (expired(row.expires_at || row.proposal?.expires_at) ? 'expired' : row.approval_id || row.approval ? 'approved' : 'awaiting approval');
}
export function canExecute(actor, detail) {
  return actor?.role === 'operator' && actor.id === detail.proposal.actor_id && !!detail.approval &&
    !expired(detail.approval.expires_at) && !detail.operation;
}
export function executionKey(storage, actor, proposalId, uuid) {
  const key = `odoo-ops:${actor.tenant_id}:${actor.id}:${proposalId}`;
  let value = storage.getItem(key);
  if (!/^[a-f0-9-]{36}$/.test(value || '')) { value = uuid(); storage.setItem(key, value); }
  return value;
}
