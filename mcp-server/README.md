# Odoo Business Operations MCP server

Executable TypeScript stdio server and reference client, using official SDK 2.3.1
and pinned protocol 2026-07-28. Ten scoped tools call the Python domain API;
none grant approval or bypass domain authorization.

See [Phase 4 setup, tests and recovery](../docs/PHASE-4.md). Offline implementation
is complete; downstream connected validation belongs to Phase 6.
