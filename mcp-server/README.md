# MCP server boundary

Implementation is scheduled for Phase 4. The TypeScript reference client currently
uses the local HTTP domain API. This directory defines the boundary; it is not an
executable MCP server. Read/prepare/execute/status contracts remain specified in
[MCP-INTEGRATIONS.md](../MCP-INTEGRATIONS.md).

MCP will call the Python domain service with authenticated actor/tenant context;
it must not bypass service authorization or write to the database directly.
