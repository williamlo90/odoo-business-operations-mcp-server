/* Connected synthetic acceptance: MCP preparation -> browser approval -> MCP execution. */
const {chromium}=require('playwright');
const {execFileSync}=require('node:child_process');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'../..');
process.loadEnvFile(process.env.ODOO_OPS_ENV_FILE||path.join(root,'.env'));
const base='http://127.0.0.1:'+(process.env.API_PORT||'8020');
const output=path.join(root,'local/web-acceptance');fs.mkdirSync(output,{recursive:true});
const checks=[];let browser;
function tool(name,args={},role='operator.a'){
  const raw=execFileSync('node',['mcp-server/dist/cli.js',name,JSON.stringify(args)],{cwd:root,env:{...process.env,DEMO_USERNAME:role,API_URL:base},encoding:'utf8',timeout:45000});
  const response=JSON.parse(raw);assert.ok(!response.isError,JSON.stringify(response).slice(0,350));
  return response.structuredContent?.data||JSON.parse(response.content[0].text).data;
}
async function login(page,role){await page.locator('#username').fill(role);await page.locator('#password').fill(process.env.DEMO_PASSWORD);await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.getByRole('heading',{name:'Quotation review'}).waitFor();}
(async()=>{
  const customer=tool('odoo.customer_search',{query:'OPS-A-001'}).items.find(x=>x.reference==='OPS-A-001');assert.ok(customer);
  const catalog=tool('odoo.catalog').items;const one=catalog.find(x=>x.code==='OPS-A-P1'),two=catalog.find(x=>x.code==='OPS-A-P2');assert.ok(one&&two);
  checks.push('MCP source lookup and catalog');
  const proposal=tool('odoo.quote_prepare',{customer_id:customer.id,items:[{product_id:one.id,quantity:2},{product_id:two.id,quantity:1}]});
  assert.equal(Number(proposal.preview.total),250000);checks.push('MCP quotation preparation');
  browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1280,height:900}});
  const errors=[];page.on('pageerror',err=>errors.push(err.message));await page.goto(base+'/#proposal/'+proposal.id);await login(page,'approver.a');
  assert.equal(await page.locator('#execute').count(),0);assert.equal(await page.getByRole('button',{name:'Create in Odoo'}).count(),0);
  await page.screenshot({path:path.join(output,'approval-before.png'),fullPage:true});
  await page.locator('#review-check').check();await page.getByRole('button',{name:'Approve proposal'}).click();await page.locator('#approval-id').waitFor();
  const review=tool('odoo.review_status',{proposal_id:proposal.id});assert.equal(review.approval_id,await page.locator('#approval-id').textContent());
  checks.push('independent browser approval and MCP handoff');
  const key=require('node:crypto').randomUUID();const args={proposal_id:proposal.id,approval_id:review.approval_id,idempotency_key:key};
  const operation=tool('odoo.execute_approved',args);assert.equal(operation.status,'verified');
  const replay=tool('odoo.execute_approved',args);assert.equal(replay.id,operation.id);
  const status=tool('odoo.operation_status',{operation_id:operation.id});assert.equal(status.id,operation.id);assert.equal(status.status,'verified');
  assert.match(operation.id,/^[a-f0-9-]{36}$/);
  const sql=`SELECT (SELECT count(*) FROM ops_operation WHERE operation_id='${operation.id}'),(SELECT count(*) FROM sale_order WHERE client_order_ref='ops:${operation.id}');`;
  const counts=execFileSync('docker',['compose','-f','compose.yaml','-f','compose.odoo.yaml','exec','-T','odoo-db','psql','-U','odoo','-d','odoo_ops_sandbox','-At','-c',sql],{cwd:root,encoding:'utf8',timeout:30000}).trim();
  assert.equal(counts,'1|1');checks.push('MCP execution, status and replay preserve one ledger and Odoo order');
  await page.getByRole('button',{name:'Refresh'}).click();await page.getByText('Odoo outcome').waitFor();await page.screenshot({path:path.join(output,'approval-after.png'),fullPage:true});
  const foreign=await browser.newPage();await foreign.goto(base+'/#proposal/'+proposal.id);await foreign.locator('#username').fill('operator.b');await foreign.locator('#password').fill(process.env.DEMO_PASSWORD);await foreign.getByRole('button',{name:'Sign in',exact:true}).click();await foreign.getByRole('alert').filter({hasText:'proposal not found'}).waitFor();
  checks.push('cross-company review denied');assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(output,'result.json'),JSON.stringify({recorded_at:new Date().toISOString(),checks,proposal_id:proposal.id,approval_id:review.approval_id,operation_id:operation.id,ledger_count:1,order_count:1,odoo_record:status.result.record},null,2));
  console.log(JSON.stringify({passed:checks.length,checks,operation_id:operation.id}));
})().catch(err=>{console.error(err.stack);process.exitCode=1;}).finally(async()=>{await browser?.close();});
