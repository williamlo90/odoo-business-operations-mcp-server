/* Real browser acceptance against the synthetic local Odoo stack. Creates a
   quotation and CRM activity through the normal UI; never contacts a model. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'../..');
process.loadEnvFile(path.join(root,'.env'));
const base='http://127.0.0.1:'+(process.env.API_PORT||'8020');
const output=path.join(root,'local/web-acceptance');fs.mkdirSync(output,{recursive:true});
const errors=[], checks=[];
let browser;
const ready=page=>page.waitForFunction(()=>!document.querySelector('#app').hasAttribute('aria-busy'));
async function login(page,username){
  await page.locator('#username').fill(username);await page.locator('#password').fill(process.env.DEMO_PASSWORD);
  await page.getByRole('button',{name:'Sign in to workspace'}).click();
  await page.locator('.sidebar').waitFor();await ready(page);
}
async function shot(page,name){await ready(page);await page.screenshot({path:path.join(output,name+'.png'),fullPage:true,animations:'disabled'});}
async function approve(page,id){
  await page.goto(base+'/#proposal/'+id);
  if(await page.locator('#username').count())await login(page,'approver.a');
  await ready(page);await page.locator('#review-check').check();
  await page.getByRole('button',{name:'Approve proposal',exact:true}).click();await ready(page);
  await page.getByText('Approval recorded. The original operator can now execute.').waitFor();
}
(async()=>{
  browser=await chromium.launch({headless:true});
  const ctx=await browser.newContext({viewport:{width:1440,height:1000}});
  const page=await ctx.newPage();page.on('pageerror',err=>errors.push(err.message));
  await page.goto(base);await shot(page,'login');await login(page,'operator.a');
  await page.getByRole('heading',{name:'Work queue'}).waitFor();checks.push('authenticated queue');
  await page.getByRole('button',{name:'New quotation',exact:true}).click();await ready(page);
  await page.getByLabel('Customer name or reference').fill('OPS-A-001');
  await page.getByRole('button',{name:'Search',exact:true}).click();await ready(page);
  await page.locator('input[name=customer]').check();
  await page.locator('.line select').selectOption({label:await page.locator('.line option').filter({hasText:'OPS-A-P1'}).textContent()});
  await page.locator('.line input').fill('2');await page.getByRole('button',{name:'+ Add line',exact:true}).click();
  await page.locator('.line select').nth(1).selectOption({label:await page.locator('.line').nth(1).locator('option').filter({hasText:'OPS-A-P2'}).textContent()});
  await shot(page,'prepare');
  await page.getByRole('button',{name:'Prepare quotation preview'}).click();await ready(page);
  await page.getByRole('heading',{name:'Quotation review'}).waitFor();
  const id=new URL(page.url()).hash.split('/')[1];assert.ok(id);
  assert.equal(await page.locator('#approve').count(),0);checks.push('operator cannot approve in UI');
  assert.ok((await page.locator('.summary.total').innerText()).includes('250,000'));
  await shot(page,'proposal');checks.push('source-backed quotation preview');
  const approverContext=await browser.newContext({viewport:{width:1440,height:1000}});
  const ap=await approverContext.newPage();ap.on('pageerror',err=>errors.push(err.message));
  await approve(ap,id);checks.push('separate approver');
  await page.getByRole('button',{name:'Refresh',exact:true}).click();await ready(page);
  // Let Odoo commit, then discard the HTTP response at the browser boundary.
  await page.route('**/v1/proposals/'+id+'/execute',async route=>{await route.fetch();await route.abort('failed');},{times:1});
  await page.locator('#execute-check').check();await page.getByRole('button',{name:'Create in Odoo',exact:true}).click();await ready(page);
  await page.getByRole('heading',{name:'Verified in Odoo',exact:true}).waitFor();
  const receipt=JSON.parse(await page.locator('.receipt pre').textContent());
  assert.equal(receipt.status,'verified');assert.equal(Number(receipt.result.record.total),250000);
  checks.push('lost execution response recovered from saved server operation');
  await page.getByRole('button',{name:'Refresh',exact:true}).click();await ready(page);
  await shot(page,'receipt');checks.push('real Odoo quotation verified');
  await page.reload();await login(page,'operator.a');
  await page.getByRole('heading',{name:'Verified in Odoo',exact:true}).waitFor();
  const restored=JSON.parse(await page.locator('.receipt pre').textContent());assert.equal(restored.id,receipt.id);
  assert.equal(await page.locator('#execute').count(),0);checks.push('reload and reauthentication preserve operation');
  await page.getByRole('button',{name:'Check Odoo status',exact:true}).click();await ready(page);
  assert.equal(JSON.parse(await page.locator('.receipt pre').textContent()).id,receipt.id);
  checks.push('status reconciliation retains original operation');
  const bctx=await browser.newContext();const bp=await bctx.newPage();await bp.goto(base+'/#proposal/'+id);await login(bp,'operator.b');
  await bp.getByRole('alert').filter({hasText:'proposal not found'}).waitFor();assert.equal(await bp.locator('.receipt').count(),0);checks.push('cross-company proposal denied');
  await page.getByRole('button',{name:'CRM follow-up',exact:true}).click();await ready(page);
  const options=await page.locator('#opportunity option').allTextContents();assert.ok(options.length>1);
  await page.locator('#opportunity').selectOption({index:1});await page.locator('#due').fill('2026-12-15');
  await page.locator('#summary').fill('Review quotation after browser acceptance');
  await page.getByRole('button',{name:'Prepare activity preview'}).click();await ready(page);
  const activityId=new URL(page.url()).hash.split('/')[1];await approve(ap,activityId);
  await page.getByRole('button',{name:'Refresh',exact:true}).click();await ready(page);await page.locator('#execute-check').check();
  await page.getByRole('button',{name:'Create in Odoo',exact:true}).click();await ready(page);
  await page.getByRole('heading',{name:'Verified in Odoo',exact:true}).waitFor();
  const activity=JSON.parse(await page.locator('.receipt pre').textContent());assert.equal(activity.result.record.kind,'activity');checks.push('real CRM activity prepared, approved and verified');
  await page.getByRole('button',{name:'Work queue',exact:true}).click();await ready(page);await shot(page,'queue');
  await page.setViewportSize({width:390,height:844});await shot(page,'mobile');
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));checks.push('390px responsive layout');
  await page.getByRole('button',{name:'Sign out',exact:true}).click();await ready(page);await page.locator('#username').waitFor();
  assert.equal(await page.locator('.receipt').count(),0);checks.push('logout clears private workspace');
  assert.deepEqual(errors,[]);checks.push('no browser JavaScript errors');
  fs.writeFileSync(path.join(output,'result.json'),JSON.stringify({date:new Date().toISOString(),checks,quote_proposal:id,quote_operation:receipt.id,quote_record:receipt.result.record.name,activity_proposal:activityId,activity_operation:activity.id},null,2));
  console.log(JSON.stringify({passed:checks.length,checks},null,2));
})().catch(err=>{console.error(err.message);process.exitCode=1;}).finally(async()=>{if(browser)await browser.close();});
