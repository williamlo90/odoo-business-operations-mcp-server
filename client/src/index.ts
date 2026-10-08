import assert from "node:assert/strict";

const base = process.env.API_URL ?? "http://127.0.0.1:8020";
const username = process.env.DEMO_USERNAME ?? "operator.a";
const password = process.env.DEMO_PASSWORD;
let token: string | undefined;

async function request(path: string, method = "GET", body?: unknown): Promise<any> {
  const response = await fetch(new URL(path, base), {
    method, headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(10_000), redirect: "error",
  });
  if (!response.ok) throw new Error(`API ${response.status} at ${path}`);
  return response.status === 204 ? undefined : response.json();
}

async function main() {
  if (!password || password.length < 16) throw new Error("Set DEMO_PASSWORD from the local .env");
  const url = new URL(base);
  if (!['127.0.0.1', 'localhost', 'api'].includes(url.hostname) || url.protocol !== 'http:') {
    throw new Error('Phase 1 client only accepts the local HTTP API');
  }
  const login = await request('/auth/login', 'POST', { username, password });
  assert.equal(typeof login.access_token, 'string');
  token = login.access_token;
  try {
    const me = await request('/me');
    const customers = await request('/customers');
    assert.ok(Array.isArray(customers.items) && customers.items.length > 0);
    // Explicit synthetic reference, never choose an ambiguous name automatically.
    const reference = process.env.DEMO_CUSTOMER_REFERENCE ?? 'A-001';
    const customer = customers.items.find((item: {reference: string}) => item.reference === reference);
    assert.ok(customer, 'The requested synthetic customer reference is not in the permitted page');
    const created = await request('/work-requests', 'POST', {customer_id: customer.id, intent: 'research_customer'});
    const verified = await request(`/work-requests/${created.id}`);
    assert.equal(verified.status, 'recorded_local');
    assert.equal(verified.customer_id, customer.id);
    assert.equal(verified.tenant_id, me.tenant_id);
    assert.equal(verified.actor_id, me.id);
    console.log(JSON.stringify({result: 'passed', source: 'synthetic_local', role: me.role,
      customer_reference: reference, work_request_id: verified.id, status: verified.status}, null, 2));
  } finally {
    await request('/auth/logout', 'POST');
    token = undefined;
  }
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : 'Client failed');
  process.exitCode = 1;
});
