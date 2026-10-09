import { McpServer, fromJsonSchema } from '@modelcontextprotocol/server';
import { serveStdio } from '@modelcontextprotocol/server/stdio';
import { readFileSync } from 'node:fs';
import { randomUUID } from 'node:crypto';

const schemas = JSON.parse(readFileSync(new URL('../../contracts/v1/schemas.json', import.meta.url), 'utf8')).schemas;
const uuid = {type:'string', format:'uuid'};
const integer = {type:'integer', minimum:1};
const text = {type:'string', maxLength:500};
const obj = (properties: Record<string, any>, required = Object.keys(properties)) => ({type:'object', properties, required, additionalProperties:false});
const row = obj({id:integer,name:text,reference:text,company_id:integer,source:{const:'odoo:res.partner'},version:text});
const lead = obj({id:integer,name:text,company_id:integer,customer_id:integer,owner_id:integer,stage:text,source:{const:'odoo:crm.lead'},version:text});
const list = (items: any) => ({type:'array',items,maxItems:100});
const reader = ['operator','approver','auditor'];
const stable = (value:any):string => JSON.stringify(value,(_key,item)=>item && typeof item==='object' && !Array.isArray(item) ? Object.fromEntries(Object.entries(item).sort(([a],[b])=>a.localeCompare(b))) : item);
type Spec = {name:string; description:string; input:any; output:any; roles:string[]; method?:string;
  path:(args:any)=>string; body?:(args:any)=>unknown; map?:(data:any)=>unknown};
const specs: Spec[] = [
  {name:'odoo.identity',description:'Read authenticated identity; scope cannot be supplied by the caller.',input:obj({}),
    output:obj({id:uuid,tenant_id:uuid,role:{enum:reader}}),roles:reader,path:()=>'/me'},
  {name:'odoo.customer_search',description:'Read one revision-bound customer page within authenticated scope.',
    input:obj({query:{type:'string',maxLength:100},after:{type:'integer',minimum:0},limit:{type:'integer',minimum:1,maximum:100},revision:{type:'string',pattern:'^[a-f0-9]{64}$'}},['query']),
    output:obj({items:list(row),next_cursor:{anyOf:[integer,{type:'null'}]},revision:{type:'string',pattern:'^[a-f0-9]{64}$'},ambiguous:{type:'boolean'}}),
    roles:reader,path:a=>'/v1/customers?'+new URLSearchParams(Object.entries(a).map(([k,v])=>[k,String(v)]))},
  {name:'odoo.catalog',description:'Read the supported product catalog and pricing policy.',input:obj({}),
    output:obj({items:list(obj({id:integer,code:text,name:text,unit_price:{type:'string'}})),currency:text,pricing_policy:text}),roles:reader,path:()=>'/v1/catalog'},
  {name:'odoo.opportunity_list',description:'Read opportunities in authenticated company scope.',input:obj({}),
    output:obj({items:list(lead)}),roles:reader,path:()=>'/v1/opportunities'},
  {name:'odoo.opportunity_get',description:'Read one scoped opportunity, with source reference.',input:obj({opportunity_id:integer}),
    output:lead,roles:reader,path:a=>'/v1/opportunities/'+a.opportunity_id},
  {name:'odoo.quote_prepare',description:'Prepare a quote proposal. Does not approve or create an Odoo order.',input:schemas.QuoteInput,
    output:schemas.ProposalOut,roles:['operator'],method:'POST',path:()=>'/v1/quotes/prepare',body:a=>a},
  {name:'odoo.activity_prepare',description:'Prepare an activity proposal; human approval is still required.',input:schemas.ActivityInput,
    output:schemas.ProposalOut,roles:['operator'],method:'POST',path:()=>'/v1/activities/prepare',body:a=>a},
  {name:'odoo.proposal_get',description:'Read an immutable proposal for human preview.',input:obj({proposal_id:uuid}),
    output:schemas.ProposalOut,roles:reader,path:a=>'/v1/proposals/'+a.proposal_id},
  {name:'odoo.review_status',description:'Read a scoped human approval handoff and saved operation status. Returns approval ID after independent browser review; never grants approval.',
    input:obj({proposal_id:uuid}),output:obj({proposal_id:uuid,approval_id:{anyOf:[uuid,{type:'null'}]},approval_expires_at:{anyOf:[{type:'string',format:'date-time'},{type:'null'}]},operation_id:{anyOf:[uuid,{type:'null'}]},operation_status:{anyOf:[text,{type:'null'}]}}),roles:reader,
    path:a=>'/v1/workspace/proposals/'+a.proposal_id,
    map:d=>({proposal_id:d.proposal.id,approval_id:d.approval?.id??null,approval_expires_at:d.approval?.expires_at??null,operation_id:d.operation?.id??null,operation_status:d.operation?.status??null})},
  {name:'odoo.execute_approved',description:'Execute an existing human-approved proposal using its stable idempotency key. Never creates approval.',
    input:obj({proposal_id:uuid,approval_id:uuid,idempotency_key:uuid}),output:schemas.OperationOut,roles:['operator'],method:'POST',
    path:a=>'/v1/proposals/'+a.proposal_id+'/execute',body:a=>({approval_id:a.approval_id,idempotency_key:a.idempotency_key})},
  {name:'odoo.operation_status',description:'Reconcile an operation and return authoritative status; never retries an Odoo write.',
    input:obj({operation_id:uuid}),output:schemas.OperationOut,roles:reader,path:a=>'/v1/operations/'+a.operation_id},
];

const errorCodes = new Set(['invalid_session','authentication_required','role_not_permitted','stale_proposal','source_changed',
  'approval_expired','idempotency_conflict','proposal_not_found','operation_not_found','payload_mismatch','self_approval',
  'invalid_input','invalid_due_date','invalid_assignee','unsupported_pricing','unsupported_product','database_unavailable']);
class Failure extends Error {}

export function buildServer() {
  const base = new URL(process.env.API_URL ?? 'http://127.0.0.1:8020');
  if (base.protocol !== 'http:' || !['127.0.0.1','localhost'].includes(base.hostname) || base.username || base.password || base.search || base.hash || base.pathname !== '/') throw new Failure('invalid_api_url');
  const token = process.env.ODOO_OPS_TOKEN;
  if (!token || token.length > 256) throw new Failure('session_required');
  const timeout = Number(process.env.MCP_DOMAIN_TIMEOUT_MS ?? '10000');
  if (!Number.isInteger(timeout) || timeout < 100 || timeout > 10000) throw new Failure('invalid_timeout');
  let active = 0;
  const server = new McpServer({name:'odoo-business-operations',version:'0.4.0'});

  async function request(path:string, method:string, body:unknown, signal:AbortSignal, correlation:string, links:string[]) {
    try {
      const response = await fetch(new URL(path,base), {method, redirect:'error',
        headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},
        body:body === undefined ? undefined : JSON.stringify(body), signal:AbortSignal.any([signal,AbortSignal.timeout(timeout)])});
      const reader = response.body?.getReader();
      const chunks:Uint8Array[] = []; let size = 0;
      if (reader) {
        try { for (;;) { const {done,value} = await reader.read(); if (done) break;
          size += value.length; if (size > 262144) { await reader.cancel(); throw new Failure('response_too_large'); } chunks.push(value); }
        } finally { reader.releaseLock(); }
      }
      const data = JSON.parse(Buffer.concat(chunks).toString('utf8'));
      const domainId = response.headers.get('x-correlation-id');
      if (domainId && /^[a-f0-9-]{36}$/.test(domainId)) {
        links.push(domainId);
        console.error(JSON.stringify({event:'mcp_domain',correlation_id:correlation,domain_correlation_id:domainId}));
      }
      if (!response.ok) {
        if (method === 'POST' && response.status >= 500) throw new Failure('write_outcome_unknown');
        throw new Failure(errorCodes.has(data?.error) ? data.error : response.status === 401 || response.status === 403 ? 'access_denied' : 'domain_rejected');
      }
      return data;
    } catch (error) {
      if (error instanceof Failure) throw error;
      if (signal.aborted) throw new Failure('request_cancelled');
      throw new Failure(method === 'POST' ? 'write_outcome_unknown' : 'domain_unavailable');
    }
  }
  for (const spec of specs) {
    const {$defs,...dataSchema} = spec.output;
    const output = {...obj({contract_version:{const:'1.0'},correlation_id:uuid,domain_correlation_ids:{type:'array',items:uuid,maxItems:3},data:dataSchema}),...($defs ? {$defs} : {})};
    const validator = fromJsonSchema<any>(spec.output);
    server.registerTool(spec.name, {description:spec.description, inputSchema:fromJsonSchema<any>(spec.input),
      outputSchema:fromJsonSchema<any>(output), annotations:{readOnlyHint:spec.method !== 'POST',destructiveHint:false,idempotentHint:spec.name !== 'odoo.quote_prepare' && spec.name !== 'odoo.activity_prepare',openWorldHint:false}},
      async (args, ctx) => {
        const correlation = randomUUID(); const started = Date.now(); const domainIds:string[]=[];
        if (active >= 4) return {isError:true,content:[{type:'text' as const,text:JSON.stringify({error:'request_limit',correlation_id:correlation})}]};
        active++;
        try {
          const signal = ctx.mcpReq.signal;
          const me = await request('/me','GET',undefined,signal,correlation,domainIds);
          if (!me || !/^[a-f0-9-]{36}$/.test(me.id) || !/^[a-f0-9-]{36}$/.test(me.tenant_id)) throw new Failure('invalid_identity');
          if (!spec.roles.includes(me.role)) throw new Failure('role_not_permitted');
          if (spec.name === 'odoo.execute_approved') {
            const proposal = await request('/v1/proposals/'+args.proposal_id,'GET',undefined,signal,correlation,domainIds);
            if (proposal.actor_id !== me.id || proposal.tenant_id !== me.tenant_id) throw new Failure('access_denied');
          }
          let data = spec.name === 'odoo.identity' ? {id:me.id,tenant_id:me.tenant_id,role:me.role} :
            await request(spec.path(args),spec.method ?? 'GET',spec.body?.(args),signal,correlation,domainIds);
          if (spec.map) data=spec.map(data);
          const checked = await validator['~standard'].validate(data);
          if (checked.issues) throw new Failure(spec.method === 'POST' ? 'write_outcome_unknown' : 'domain_response_malformed');
          if (data.tenant_id && data.tenant_id !== me.tenant_id) throw new Failure('scope_mismatch');
          if (spec.name === 'odoo.quote_prepare' || spec.name === 'odoo.activity_prepare') {
            const kind=spec.name === 'odoo.quote_prepare' ? 'quote' : 'activity';
            if(data.actor_id!==me.id || data.kind!==kind || stable(data.payload)!==stable(args)) throw new Failure('write_outcome_unknown');
          }
          if (spec.name === 'odoo.execute_approved' && (data.proposal_id !== args.proposal_id || data.approval_id !== args.approval_id || data.idempotency_key !== args.idempotency_key)) throw new Failure('write_outcome_unknown');
          if (spec.name === 'odoo.operation_status' && data.id !== args.operation_id) throw new Failure('scope_mismatch');
          if (data.status === 'verified' && (!data.result || data.result.operation_id !== data.id)) throw new Failure('invalid_verified_receipt');
          const result = {contract_version:'1.0',correlation_id:correlation,domain_correlation_ids:domainIds,data};
          return {structuredContent:result,content:[{type:'text' as const,text:JSON.stringify(result)}]};
        } catch (error) {
          return {isError:true,content:[{type:'text' as const,text:JSON.stringify({error:error instanceof Failure ? error.message : 'tool_failed',correlation_id:correlation})}]};
        } finally {
          active--; console.error(JSON.stringify({event:'mcp_tool',tool:spec.name,correlation_id:correlation,duration_ms:Date.now()-started}));
        }
      });
  }
  return server;
}

try { serveStdio(buildServer); }
catch { console.error('mcp_startup_failed'); process.exitCode=1; }
