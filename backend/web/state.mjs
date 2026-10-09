export const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const expired = value => !value || !Number.isFinite(Date.parse(value)) || Date.parse(value) <= Date.now();
export function proposalState(row) {
  return row.operation_status || row.operation?.status || (expired(row.expires_at || row.proposal?.expires_at) ? 'expired' : row.approval_id || row.approval ? 'approved' : 'awaiting approval');
}
