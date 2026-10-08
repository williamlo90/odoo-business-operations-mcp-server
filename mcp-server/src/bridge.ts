// Private host IPC bridge. The downstream connection uses the official MCP client.
import { createInterface } from 'node:readline';
import { connectMcp } from './connection.js';

const {client} = await connectMcp();
const lines = createInterface({input:process.stdin,crlfDelay:Infinity});
try {
  for await (const line of lines) {
    let id:unknown = null;
    try {
      if (Buffer.byteLength(line)>16384) throw new Error();
      const value=JSON.parse(line); id=value.id;
      if (!Number.isInteger(id) || typeof value.tool !== 'string') throw new Error();
      const result=await client.callTool({name:value.tool,arguments:value.arguments ?? {}},{timeout:15000});
      console.log(JSON.stringify({id,result}));
    } catch { console.log(JSON.stringify({id,error:'mcp_call_failed'})); }
  }
} finally { await client.close(); }
