import { Client } from '@modelcontextprotocol/client';
import { StdioClientTransport } from '@modelcontextprotocol/client/stdio';
import { fileURLToPath } from 'node:url';

export async function connectMcp(environment:Record<string,string> = {}) {
  const env:Record<string,string> = {};
  for (const name of ['PATH','Path','SystemRoot','SYSTEMROOT','TEMP','TMP','API_URL','ODOO_OPS_TOKEN','MCP_DOMAIN_TIMEOUT_MS']) {
    const value=process.env[name]; if (value) env[name]=value;
  }
  Object.assign(env,environment);
  const transport = new StdioClientTransport({command:process.execPath,
    args:[fileURLToPath(new URL('./server.js',import.meta.url))],env,stderr:'pipe'});
  const client = new Client({name:'odoo-ops-reference',version:'0.4.0'},
    {versionNegotiation:{mode:{pin:'2026-07-28'}}});
  try {
    await client.connect(transport);
    transport.stderr?.on('data', () => {});
    const version=client.getNegotiatedProtocolVersion();
    if (version !== '2026-07-28') throw new Error('unsupported_protocol');
    return {client,transport};
  } catch {
    await client.close();
    throw new Error('mcp_connection_failed');
  }
}
