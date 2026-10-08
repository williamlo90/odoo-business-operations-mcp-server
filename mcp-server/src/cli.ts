import { connectMcp } from './connection.js';

// Human-operated reference client. Approval is issued through the Phase 2 client,
// never exposed as an MCP tool. Reuse the idempotency UUID for approved execution.
async function main() {
  const base=new URL(process.env.API_URL ?? 'http://127.0.0.1:8020');
  if(base.protocol!=='http:' || !['localhost','127.0.0.1'].includes(base.hostname) || base.username || base.password || base.pathname!=='/' || base.search || base.hash)throw new Error('invalid_api_url');
  const [name,raw='{}']=process.argv.slice(2);
  if(!name || raw.length>16384)throw new Error('tool_and_bounded_json_required');
  const args=JSON.parse(raw);
  const password=process.env.DEMO_PASSWORD;
  if(!password)throw new Error('demo_password_required');
  const login=await fetch(new URL('/auth/login',base),{method:'POST',redirect:'error',signal:AbortSignal.timeout(10000),
    headers:{'Content-Type':'application/json'},body:JSON.stringify({username:process.env.DEMO_USERNAME ?? 'operator.a',password})});
  if(!login.ok)throw new Error('login_failed');
  const {access_token:token}=await login.json() as {access_token:string};
  if(typeof token!=='string' || token.length>256)throw new Error('invalid_session');
  try{
    const {client}=await connectMcp({API_URL:base.href,ODOO_OPS_TOKEN:token});
    try{
      const result=name==='list' ? await client.listTools() : await client.callTool({name,arguments:args},{timeout:30000});
      console.log(JSON.stringify(result,null,2));
      if('isError' in result && result.isError)process.exitCode=1;
    }finally{await client.close();}
  }finally{
    await fetch(new URL('/auth/logout',base),{method:'POST',redirect:'error',signal:AbortSignal.timeout(10000),headers:{Authorization:'Bearer '+token}});
  }
}
main().catch(()=>{console.error('mcp_client_failed');process.exitCode=1;});
