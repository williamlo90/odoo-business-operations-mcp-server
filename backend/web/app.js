import {escapeHTML as e, expired, proposalState, canExecute, executionKey} from './state.mjs';

const root = document.querySelector('#app');
let token = null, me = null, company = null, busy = false, sessionTimer;
let view = 'queue', offset = 0, detail = null, catalog = [], customers = [], customerId = null;
let searchQuery = '', customerCursor = null, customerRevision = null, opportunities = [];
const money = value => new Intl.NumberFormat('en-US', {style:'currency',currency:'IDR',maximumFractionDigits:0}).format(Number(value));
const when = value => new Date(value).toLocaleString('en-GB', {day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});
const badge = state => `<span class="badge ${e(state.replace(/ /g,'-'))}">${e(state)}</span>`;
const button = (id, text, primary=false) => `<button class="btn ${primary?'primary':''}" id="${id}">${text}</button>`;
const on = (id, event, action) => document.getElementById(id)?.addEventListener(event, action);
const field = (id,label,type='text',extra='') => `<div class="field"><label for="${id}">${label}</label><input id="${id}" name="${id}" type="${type}" ${extra}></div>`;

async function api(path, method='GET', body) {
  const response = await fetch(path, {method, credentials:'omit', redirect:'error',
    headers:{'Content-Type':'application/json', ...(token?{Authorization:`Bearer ${token}`}:{})},
    body:body===undefined?undefined:JSON.stringify(body), signal:AbortSignal.timeout(45000)});
  if (!response.ok) {
    const data = await response.json().catch(()=>({}));
    const code = typeof data.error==='string' && /^[a-z_]+$/.test(data.error) ? data.error : 'request_failed';
    if(response.status===401 && token) { clearSession(); loginPage('Your session expired. Sign in again to continue.'); }
    const error = new Error(code.replaceAll('_',' ')); error.code=code;
    error.correlation=response.headers.get('X-Correlation-ID'); throw error;
  }
  return response.status===204 ? null : response.json();
}
function notice(message, type='info') {
  const el=document.getElementById('notice');
  if(el){ el.innerHTML=`<div class="notice ${e(type)}" role="${type==='error'?'alert':'status'}">${e(message)}</div>`; }
}
async function run(action) {
  if(busy) return;
  busy=true; root.setAttribute('aria-busy','true');
  const controls=[...root.querySelectorAll('button,input,select,textarea')].filter(el=>!el.disabled);
  controls.forEach(el=>el.disabled=true);
  try { await action(); }
  catch(error) { const loading=document.querySelector('.busy');if(loading)loading.textContent='This view could not load. Use the navigation to try again.'; notice(error.name==='TimeoutError' || error.name==='TypeError' ?
    'The server could not be reached. A write may have completed. Refresh the proposal before taking another action.' :
    `${error.message}${error.correlation?' · Reference '+error.correlation:''}`, 'error'); }
  finally { busy=false;root.removeAttribute('aria-busy');controls.forEach(el=>{if(el.isConnected)el.disabled=false;}); }
}
function clearSession(){ token=null;me=null;company=null;detail=null;catalog=[];customers=[];opportunities=[];customerId=null;clearTimeout(sessionTimer); }
function loginPage(message='') {
  root.innerHTML=`<div class="login"><section class="login-story"><div class="brand"><span class="mark">o</span>odoo operations<small>Business workspace</small></div>
    <div><h1>Good decisions.<br>Verified outcomes.</h1><p>Prepare the right business action, review it together, and know exactly what happened in Odoo.</p>
    <div class="login-steps"><div>Prepare<span>Start with source records</span></div><div>Approve<span>Keep review independent</span></div><div>Verify<span>Get a checked receipt</span></div></div></div>
    <small>Local workspace · Odoo Community</small></section><main id="main" class="login-form"><div class="login-box"><div class="eyebrow">Your operations, in view</div><h2>Welcome back</h2>
    <p class="muted">Sign in with your assigned business account.</p><div id="notice" aria-live="polite"></div>
    <form id="login-form">${field('username','Username','text','required maxlength="100" autocomplete="username" placeholder="operator.a"')}
    ${field('password','Password','password','required maxlength="256" autocomplete="current-password"')}
    <button class="btn primary" type="submit">Sign in to workspace</button></form>
    <p class="muted">Use an operator account to prepare and execute. Use a separate approver account to review.</p></div></main></div>`;
  if(message) notice(message);
  on('login-form','submit',event=>{event.preventDefault();const username=document.querySelector('#username').value.trim(),password=document.querySelector('#password').value;
    run(async()=>{const session=await api('/auth/login','POST',{username,password});token=session.access_token;
      document.querySelector('#password').value='';
      try { me=await api('/me'); }
      catch(error){clearSession();throw error;}
      sessionTimer=setTimeout(()=>{clearSession();loginPage('Session ended. Sign in again; your proposals are saved.');},Math.max(0,Date.parse(session.expires_at)-Date.now()));
      shell();await route();});});
}
function shell() {
  root.innerHTML=`<div class="shell"><aside class="sidebar"><div class="brand"><span class="mark">o</span>operations<small>Odoo business workspace</small></div>
    <nav aria-label="Workspace"><button class="nav" data-view="queue">Work queue</button>${me.role==='operator'?'<button class="nav" data-view="quote">New quotation</button><button class="nav" data-view="activity">CRM follow-up</button>':''}<button class="nav" data-view="help">Workflow guide</button></nav>
    <div class="foot"><div class="stage-label">Connected to your business</div>Prepare. Review. Verify.<br>Local Odoo environment</div></aside>
    <div><header class="topbar"><span class="muted" id="company-label">Company scope enforced</span><div class="identity"><span class="avatar">${e(me.username.slice(0,1).toUpperCase())}</span><div><strong>${e(me.username)}</strong><span class="muted">${e(me.role)}</span></div>${button('logout','Sign out')}</div></header>
    <main id="main" class="content" tabindex="-1"><div id="notice" aria-live="polite"></div><div id="screen"></div></main></div></div>`;
  root.querySelectorAll('[data-view]').forEach(el=>el.addEventListener('click',()=>{if(!busy){history.replaceState(null,'','#'+el.dataset.view);run(route);}}));
  on('logout','click',()=>run(async()=>{await api('/auth/logout','POST');clearSession();history.replaceState(null,'','#queue');loginPage('You have signed out.');}));
}
function screen(html){document.querySelector('#screen').innerHTML=html;document.querySelector('#notice').innerHTML='';}
function heading(title,subtitle,actions=''){return `<div class="pagehead"><div><div class="eyebrow">Sales operations</div><h1>${title}</h1><p>${subtitle}</p></div><div class="actions">${actions}</div></div>`;}
async function route(){
  if(!me)return;
  view=location.hash.slice(1)||'queue';
  root.querySelectorAll('[data-view]').forEach(el=>{el.classList.toggle('active',el.dataset.view===view || (view.startsWith('proposal/')&&el.dataset.view==='queue'));el.setAttribute('aria-current',el.classList.contains('active')?'page':'false');});
  screen('<p class="busy" role="status">Loading workspace…</p>');
  if(view.startsWith('proposal/')) await openProposal(view.slice(9));
  else if(view==='quote'&&me.role==='operator') await quotePage();
  else if(view==='activity'&&me.role==='operator') await activityPage();
  else if(view==='help') helpPage();
  else await queuePage();
  // Company identity is optional to the saved queue when Odoo is unavailable.
  if(!company){try{company=await api('/v1/odoo/info');}catch{/* Queue and saved proposals remain useful during Odoo outages. */}}
  const label=document.querySelector('#company-label');if(label&&company)label.textContent=`Company ${company.company_id} · ${company.edition}`;
}
async function queuePage(){
  const [rows,metrics]=await Promise.all([api('/v1/workspace/proposals?limit=10&offset='+offset),api('/v1/metrics')]);
  screen(heading('Work queue','Every proposal has a clear next step. Review the source, keep approval separate, and track the result.',
    button('refresh','Refresh')+(me.role==='operator'?button('new-quote','+ New quotation',true):''))+
    `<section class="stats" aria-label="Company totals"><div class="stat"><span>Proposals prepared</span><strong>${metrics.proposals}</strong><small>All time · current company</small></div><div class="stat"><span>Verified outcomes</span><strong>${metrics.operations.verified}</strong><small>Checked against Odoo</small></div><div class="stat"><span>Needs attention</span><strong>${metrics.operations.unknown+metrics.operations.dispatched+metrics.operations.review+metrics.operations.failed}</strong><small>Unresolved or failed</small></div></section>
    <section class="panel flush"><div class="panelhead"><h2>Recent proposals</h2><span class="muted">Newest first</span></div>
    ${rows.items.length?`<div class="table-scroll"><table class="queue-table"><thead><tr><th>Proposal / customer</th><th>Created</th><th>Amount / due</th><th>Status</th><th><span class="muted">Review</span></th></tr></thead><tbody>${rows.items.map(p=>`<tr><td><strong>${e(p.kind==='quote'?p.preview.customer_name:p.preview.summary)}</strong><small>${p.kind==='quote'?'Quotation':'CRM activity'} · ${e(p.id.slice(0,8))}</small></td><td>${e(when(p.created_at))}</td><td>${e(p.kind==='quote'?money(p.preview.total):p.preview.due_date)}</td><td>${badge(proposalState(p))}</td><td><button class="btn small" data-open="${e(p.id)}" aria-label="Open proposal ${e(p.id.slice(0,8))}">Open</button></td></tr>`).join('')}</tbody></table></div>`:'<div class="empty"><h2>No proposals yet</h2><p>Prepared quotations and follow-ups will appear here.</p></div>'}
    <div class="paging"><span>${rows.items.length?`${offset+1}–${offset+rows.items.length}`:'0'} shown</span><div class="actions"><button class="btn small" id="previous" ${offset===0?'disabled':''}>Previous</button><button class="btn small" id="next" ${rows.next_offset===null?'disabled':''}>Next</button></div></div></section>
    <form id="lookup" class="search"><input aria-label="Proposal ID" id="lookup-id" placeholder="Open a proposal by its full ID" required pattern="[a-fA-F0-9-]{36}"><button class="btn" type="submit">Open proposal</button></form>`);
  on('refresh','click',()=>run(queuePage));on('new-quote','click',()=>navigate('quote'));
  on('previous','click',()=>run(async()=>{offset=Math.max(0,offset-10);await queuePage();}));on('next','click',()=>run(async()=>{offset=rows.next_offset;await queuePage();}));
  root.querySelectorAll('[data-open]').forEach(el=>el.addEventListener('click',()=>navigate('proposal/'+el.dataset.open)));
  on('lookup','submit',event=>{event.preventDefault();navigate('proposal/'+document.querySelector('#lookup-id').value.trim());});
}
function navigate(path){if(busy)return;history.replaceState(null,'','#'+path);run(route);}
async function quotePage(){
  catalog=(await api('/v1/catalog')).items;customerId=null;
  screen(heading('New quotation','Choose an exact customer and the items to quote. Odoo calculates the final prices before approval.')+
    `<div class="twocol"><div><section class="panel"><h2>1. Select a customer</h2><form id="search-form" class="search"><input id="customer-query" aria-label="Customer name or reference" maxlength="100" placeholder="Search name or reference, e.g. OPS-A-001"><button class="btn" type="submit">Search</button></form><div id="customers"></div></section>
    <form id="quote-form" class="panel"><h2>2. Add line items</h2><p class="muted">Select products from the company catalog.</p><div id="lines"></div>${button('add-line','+ Add line')}<div class="rule"></div><button class="btn primary" id="prepare-quote" type="submit">Prepare quotation preview</button></form></div>
    <aside><section class="panel"><div class="eyebrow">Before you continue</div><h2>A preview comes first.</h2><p class="muted">Preparing a proposal does not create a quotation in Odoo. A separate approver reviews the exact customer, quantities and total.</p><div class="rule"></div><h3>Your workflow</h3><p>Prepare proposal<br>Request independent approval<br>Create and verify Odoo draft</p></section></aside></div>`);
  document.querySelector('#add-line').type='button';addLine();
  on('add-line','click',()=>{if(!busy)addLine();});
  on('search-form','submit',event=>{event.preventDefault();searchQuery=document.querySelector('#customer-query').value.trim();run(()=>searchCustomers(false));});
  on('quote-form','submit',event=>{event.preventDefault();if(!customerId){notice('Select an exact customer before preparing the proposal.','error');return;}
    const items=[...root.querySelectorAll('.line')].map(line=>({product_id:Number(line.querySelector('select').value),quantity:Number(line.querySelector('input').value)}));
    if(new Set(items.map(i=>i.product_id)).size!==items.length){notice('Use one line per product; combine quantities for the same item.','error');return;}
    run(async()=>{const p=await api('/v1/quotes/prepare','POST',{customer_id:customerId,items});history.replaceState(null,'','#proposal/'+p.id);await openProposal(p.id);notice('Proposal prepared. A separate approver can now review it.');});});
  searchQuery='';await searchCustomers(false);
}
function addLine(){
  if(root.querySelectorAll('.line').length>=20){notice('A quotation can contain up to 20 lines.');return;}
  const line=document.createElement('div');line.className='line';
  line.innerHTML=`<label>Product<select required><option value="">Choose a product</option>${catalog.map(p=>`<option value="${p.id}">${e(p.code)} · ${e(p.name)} · ${e(money(p.unit_price))}</option>`).join('')}</select></label><label>Quantity<input type="number" min="1" max="1000" step="1" value="1" required></label><button type="button" class="btn" aria-label="Remove line">×</button>`;
  line.querySelector('button').addEventListener('click',()=>{if(root.querySelectorAll('.line').length>1)line.remove();else notice('Keep at least one line item.');});document.querySelector('#lines').append(line);
}
async function searchCustomers(more){
  const query=new URLSearchParams({query:searchQuery,limit:'20'});
  if(more){query.set('after',customerCursor);query.set('revision',customerRevision);}
  const data=await api('/v1/customers?'+query);
  customers=more?[...customers,...data.items]:data.items;customerCursor=data.next_cursor;customerRevision=data.revision;
  if(!more)customerId=null;
  document.querySelector('#customers').innerHTML=customers.length?`${data.ambiguous?'<p class="muted">Multiple records match. Select the exact reference.</p>':''}${customers.map(c=>`<label class="customer"><input type="radio" name="customer" value="${c.id}" ${customerId===c.id?'checked':''}><span><strong>${e(c.name)}</strong><small>${e(c.reference)} · Company ${c.company_id} · Odoo record ${c.id}</small></span></label>`).join('')}${customerCursor?button('more-customers','Load more customers'):''}`:'<div class="empty">No matching customers. Try a different name or exact reference.</div>';
  root.querySelectorAll('input[name=customer]').forEach(el=>el.addEventListener('change',()=>{customerId=Number(el.value);}));on('more-customers','click',()=>run(()=>searchCustomers(true)));
}
async function activityPage(){
  opportunities=(await api('/v1/opportunities')).items;
  screen(heading('CRM follow-up','Prepare an activity against an exact opportunity. Approval is required before it appears in Odoo.')+
    `<div class="twocol"><form id="activity-form" class="panel"><div class="field"><label for="opportunity">Opportunity</label><select id="opportunity" required><option value="">Choose an opportunity</option>${opportunities.map(p=>`<option value="${p.id}">${e(p.name)} · #${p.id} · ${e(p.stage)}</option>`).join('')}</select></div>
    ${field('assignee','Assignee Odoo user ID','number','min="1" step="1" required')}${field('due','Due date','date','required')}${field('summary','Activity summary','text','maxlength="120" required placeholder="Discuss the proposed quotation"')}<button class="btn primary" type="submit">Prepare activity preview</button></form>
    <aside class="panel"><div class="eyebrow">Follow through</div><h2>Keep the context.</h2><p class="muted">The opportunity owner is suggested as the assignee. Odoo checks that the selected user belongs to the company.</p><div id="opportunity-context"></div></aside></div>`);
  on('opportunity','change',()=>{const p=opportunities.find(p=>p.id===Number(document.querySelector('#opportunity').value));document.querySelector('#assignee').value=p?.owner_id||'';document.querySelector('#opportunity-context').textContent=p?`Company ${p.company_id} · Customer record ${p.customer_id} · ${p.stage}`:'';});
  on('activity-form','submit',event=>{event.preventDefault();const payload={opportunity_id:Number(document.querySelector('#opportunity').value),assignee_id:Number(document.querySelector('#assignee').value),due_date:document.querySelector('#due').value,summary:document.querySelector('#summary').value.trim()};
    run(async()=>{const p=await api('/v1/activities/prepare','POST',payload);history.replaceState(null,'','#proposal/'+p.id);await openProposal(p.id);notice('Activity proposal prepared for independent approval.');});});
}
async function openProposal(id){
  root.querySelectorAll('[data-view]').forEach(el=>{el.classList.toggle('active',el.dataset.view==='queue');el.setAttribute('aria-current',el.dataset.view==='queue'?'page':'false');});
  if(!/^[a-f0-9-]{36}$/i.test(id)){throw new Error('Enter a valid proposal ID.');}
  detail=await api('/v1/workspace/proposals/'+encodeURIComponent(id));
  renderProposal();
}
function renderProposal(){
  const {proposal:p,approval:a,operation:o}=detail,v=p.preview,state=proposalState(detail);
  const approvalAllowed=me.role==='approver'&&p.actor_id!==me.id&&!a&&!o&&!expired(p.expires_at);
  const executeAllowed=canExecute(me,detail);
  const pending=o&&['unknown','dispatched'].includes(o.status);
  screen(heading(p.kind==='quote'?'Quotation review':'Activity review','Review the exact source data before authorizing a business action.',button('back','Back to queue')+button('refresh-detail','Refresh'))+
    `<div class="steps"><span class="step done"><b>1</b>Prepared</span><span class="step ${a?'done':''}"><b>2</b>Approved</span><span class="step ${o?.status==='verified'?'done':''}"><b>3</b>Verified in Odoo</span></div>
    <div class="twocol"><div><section class="panel"><div class="pagehead"><h2>${e(p.kind==='quote'?v.customer_name:v.summary)}</h2>${badge(state)}</div><div class="detail-meta"><div><span>Company</span><strong>${v.company_id}</strong></div><div><span>${p.kind==='quote'?'Customer record':'Opportunity record'}</span><strong>#${p.kind==='quote'?v.customer_id:v.opportunity_id}</strong></div><div><span>Approval deadline</span><strong>${e(when(p.expires_at))}</strong></div></div>
    ${p.kind==='quote'?`<div class="table-scroll"><table><thead><tr><th>Item</th><th>Qty</th><th>Unit price</th><th>Subtotal</th></tr></thead><tbody>${v.items.map(i=>`<tr><td><strong>${e(i.name)}</strong><small>Product #${i.product_id}</small></td><td>${i.quantity}</td><td>${e(money(i.unit_price))}</td><td>${e(money(i.subtotal))}</td></tr>`).join('')}</tbody></table></div><div class="summary total"><span>Quotation total</span><span>${e(money(v.total))}</span></div><p class="muted">Odoo catalog prices · No tax or discount</p>`:`<div class="summary"><span>Assignee</span><strong>Odoo user #${v.assignee_id}</strong></div><div class="summary"><span>Due date</span><strong>${e(v.due_date)}</strong></div>`}
    <details><summary>Proposal identity and source</summary><p class="code">Proposal: ${e(p.id)}<br>Payload hash: ${e(p.payload_hash)}<br>Source version: ${e(v.source_version)}</p></details></section>
    ${o?receiptHTML(o):''}</div><aside><section class="panel"><div class="eyebrow">Next action</div><h2>${o?'Inspect the outcome':a?'Ready for execution':expired(p.expires_at)?'Proposal expired':'Independent review'}</h2>
    ${approvalAllowed?`<p class="muted">Your approval applies to this exact proposal and its source version.</p><label class="check"><input id="review-check" type="checkbox"><span>I have reviewed the company, target, items or activity details, and authorize this proposal.</span></label><button class="btn primary full" id="approve" disabled>Approve proposal</button>`:
    executeAllowed?`<p class="muted">Approved by a separate account. Execution will create ${p.kind==='quote'?'one draft quotation':'one activity'} and check the Odoo result.</p><label class="check"><input id="execute-check" type="checkbox"><span>Create this approved ${p.kind==='quote'?'draft quotation':'activity'} in Odoo now.</span></label><button class="btn primary full" id="execute" disabled>Create in Odoo</button>`:
    `<p class="muted">${o?'The operation is saved. Check its status before considering another write.':expired(p.expires_at)?'Prepare a new proposal with current source data.':a?'The original operator can now execute this approved proposal.':'Ask a separate approver to sign in and open this proposal from the work queue.'}</p>`}
    ${o?button('check-status','Check Odoo status',true):''}
    ${pending&&p.actor_id===me.id&&me.role==='operator'?`<div class="rule"></div><p class="muted">If no result is found, a safe retry first reconciles Odoo and reuses the same operation.</p>${button('safe-retry','Reconcile and retry')}`:''}
    ${a?`<div class="rule"></div><div class="summary"><span>Approval</span><span>Recorded</span></div><p class="code">${e(a.id)}</p>`:''}</section>
    <section class="panel"><h3>Keep this reference</h3><p class="code">${e(p.id)}</p>${button('copy-link','Copy proposal link')}<p class="muted">Access still requires a permitted company account.</p></section></aside></div>`);
  on('back','click',()=>navigate('queue'));on('refresh-detail','click',()=>run(()=>openProposal(p.id)));
  on('copy-link','click',()=>run(async()=>{await navigator.clipboard.writeText(location.origin+'/#proposal/'+p.id);notice('Proposal link copied.');}));
  on('review-check','change',event=>{document.querySelector('#approve').disabled=!event.target.checked;});
  on('execute-check','change',event=>{document.querySelector('#execute').disabled=!event.target.checked;});
  on('approve','click',()=>run(async()=>{await api(`/v1/proposals/${p.id}/approve`,'POST',{payload_hash:p.payload_hash});await openProposal(p.id);notice('Approval recorded. The original operator can now execute.');}));
  on('execute','click',()=>run(async()=>{
    const idempotency_key=executionKey(sessionStorage,me,p.id,()=>crypto.randomUUID());
    try {await api(`/v1/proposals/${p.id}/execute`,'POST',{approval_id:a.id,idempotency_key});}
    catch(error){try{await openProposal(p.id);}catch{/* Preserve the original execution error. */}throw error;}
    await openProposal(p.id);
  }));
  on('check-status','click',()=>run(async()=>{await api('/v1/operations/'+o.id);await openProposal(p.id);}));
  on('safe-retry','click',()=>run(async()=>{await api('/v1/operations/'+o.id+'/retry','POST');await openProposal(p.id);}));
}
function receiptHTML(o){const r=o.result?.record;return `<section class="panel receipt"><div class="eyebrow">Business receipt</div><h2>${o.status==='verified'?'Verified in Odoo':o.status==='failed'?'Execution failed':o.status==='review'?'Manual review required':'Outcome not yet confirmed'}</h2>
  ${r&&o.status==='verified'?`<div class="receipt-name">${e(r.name||'Activity #'+r.external_id)}</div><div class="summary"><span>Record state</span><strong>${e(r.state||'Created')}</strong></div>${r.total?`<div class="summary"><span>Verified total</span><strong>${e(money(r.total))}</strong></div>`:''}<div class="summary"><span>Odoo record ID</span><strong>${r.external_id}</strong></div>`:'<p class="muted">Keep the operation reference. Do not create a replacement while the result is unresolved.</p>'}
  ${o.error_code?`<div class="notice error">${e(o.error_code.replaceAll('_',' '))}</div>`:''}<div class="rule"></div><p class="code">Operation: ${e(o.id)}</p><p class="muted">Last checked ${e(when(o.updated_at))} · ${o.attempts} dispatch attempt${o.attempts===1?'':'s'}</p><details><summary>Inspect sanitized receipt</summary><pre>${e(JSON.stringify(o,null,2))}</pre></details></section>`;}
function helpPage(){screen(heading('A deliberate workflow','One workspace, clear responsibilities. Business rules are enforced by the server at every step.')+
  `<div class="help-grid"><section class="panel"><div class="eyebrow">Operator</div><h2>Prepare with source records</h2><p>Select the exact customer reference, products and quantities. For CRM, choose the opportunity, assignee and due date. Review the resulting proposal before sharing its link.</p></section><section class="panel"><div class="eyebrow">Approver</div><h2>Review independently</h2><p>Sign in using your separate approver account. Open the proposal, check the company and all business details, then explicitly approve. Changed source data requires a fresh proposal.</p></section><section class="panel"><div class="eyebrow">Operator</div><h2>Execute and verify</h2><p>The original operator creates the approved record. A verified receipt means Odoo read-back matched the proposal. A draft quotation has not been confirmed or emailed.</p></section><section class="panel"><div class="eyebrow">Recovery</div><h2>Resume from the saved proposal</h2><p>If a connection drops, open the proposal from the queue and check Odoo status. Safe retry reconciles first and retains the operation identity. Failed or review states need investigation.</p></section></div><div class="notice info">Signing out or reloading clears the browser login. Proposals, approvals and operations remain saved on the server. The natural-language assistant remains available through the CLI.</div>`);}
window.addEventListener('hashchange',()=>{if(me&&!busy)run(route);});
loginPage();
