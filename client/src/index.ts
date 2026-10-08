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
  if (!response.ok) {
    const error = await response.json().catch(() => ({})) as {error?: string};
    const code = error.error && /^[a-z_]+$/.test(error.error) ? error.error : 'request_failed';
    throw new Error(`API ${response.status}: ${code}`);
  }
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
    const [command, ...args] = process.argv.slice(2);
    if (command && command !== 'foundation') {
      const need = (count: number, usage: string) => {
        if (args.length !== count) throw new Error(usage);
      };
      let result: unknown;
      if (command === 'customers') {
        result = await request('/v1/customers?query=' + encodeURIComponent(args[0] ?? ''));
      } else if (command === 'opportunities' || command === 'catalog') {
        result = await request('/v1/' + command);
      } else if (command === 'quote') {
        need(2, 'quote CUSTOMER_REFERENCE PRODUCT_CODE:QUANTITY[,PRODUCT_CODE:QUANTITY]');
        const customers = await request('/v1/customers?query=' + encodeURIComponent(args[0]!));
        const matches = customers.items.filter((c: {reference: string}) => c.reference === args[0]);
        assert.equal(matches.length, 1, 'An exact, unique customer reference is required');
        const catalog = await request('/v1/catalog');
        const items = args[1]!.split(',').map((entry: string) => {
          const [code, quantityText] = entry.split(':');
          const product = catalog.items.find((p: {code: string}) => p.code === code);
          assert.ok(product, 'Product code not available');
          const quantity = Number(quantityText);
          assert.ok(Number.isInteger(quantity) && quantity > 0 && quantity <= 1000);
          return {product_id: product.id, quantity};
        });
        result = await request('/v1/quotes/prepare', 'POST', {customer_id: matches[0].id, items});
      } else if (command === 'activity') {
        need(4, 'activity OPPORTUNITY_ID ASSIGNEE_ID YYYY-MM-DD "SUMMARY"');
        result = await request('/v1/activities/prepare', 'POST', {opportunity_id: Number(args[0]),
          assignee_id: Number(args[1]), due_date: args[2], summary: args[3]});
      } else if (command === 'preview') {
        need(1, 'preview PROPOSAL_ID');
        result = await request('/v1/proposals/' + encodeURIComponent(args[0]!));
      } else if (command === 'approve') {
        need(2, 'approve PROPOSAL_ID PAYLOAD_HASH (use an approver account after reviewing preview)');
        result = await request(`/v1/proposals/${encodeURIComponent(args[0]!)}/approve`, 'POST', {payload_hash: args[1]});
      } else if (command === 'execute') {
        need(3, 'execute PROPOSAL_ID APPROVAL_ID IDEMPOTENCY_UUID (reuse the same UUID for retries)');
        result = await request(`/v1/proposals/${encodeURIComponent(args[0]!)}/execute`, 'POST',
          {approval_id: args[1], idempotency_key: args[2]});
      } else if (command === 'status' || command === 'retry') {
        need(1, command + ' OPERATION_ID');
        result = await request('/v1/operations/' + encodeURIComponent(args[0]!) + (command === 'retry' ? '/retry' : ''), command === 'retry' ? 'POST' : 'GET');
      } else {
        throw new Error('Commands: foundation, customers, catalog, opportunities, quote, activity, preview, approve, execute, status, retry');
      }
      console.log(JSON.stringify(result, null, 2));
      return;
    }
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
