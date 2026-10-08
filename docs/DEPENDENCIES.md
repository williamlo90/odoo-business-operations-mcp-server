# Dependency register

Owner: William. Status applies to the selected local release. Missing cloud
access does not block local operation. This document contains no secret values.

| ID | Dependency | Current evidence / remaining work |
| --- | --- | --- |
| D01 | Docker engine | Local Linux stack verified; Phase 1 recorded Engine 29.8.0 |
| D02 | Windows/WSL2 and Linux containers | Startup verified without changing other project environments |
| D03 | Odoo Community 19.0 / JSON-2 | Local sandbox with Contacts, CRM, Sales and `ops_bridge`; connected read/write/read-back passed |
| D04 | Company-scoped connector keys | Private read-only API configuration; rotate according to the Odoo setup guide |
| D05 | Git repository | Phase tags and source provenance preserved; `main` presents the current release |
| D06 | Runtime/package versions | Locked Python/Node dependencies and Docker digests; Phase 1 recorded Python 3.13.16/Node 22.23.3; Phase 4 pinned MCP SDK 2.3.1/protocol 2026-07-28 |
| D07 | PostgreSQL | 17.11 validated locally; application and Odoo have separate databases/roles |
| D08 | Hosted provider access | OpenAI canary passed; Claude/Grok optional, not live-qualified |
| D09 | Local model runtime | Ollama 0.40.1 CPU; Qwen2.5 0.5B Q4_K_M, pinned digest and recorded Apache-2.0 license; experimental quality |
| D10 | Synthetic business fixtures | Companies A/B, distinct references and pricing verified with expected totals |
| D11 | Other portfolio consumers | Versioned contracts available; projects 04/05/08 are not integrated dependencies |
| D12 | Atomic Odoo write boundary | Signed envelope, READ COMMITTED transaction, source locks and unique ledger verified in connected tests |

Azure subscription, region/quota, owner CIDR, domain, budget and recipient must
be selected before Phase 10. The [Azure design](AZURE-PLAN.md) is not provisioned.
n8n is not selected. No Azure credential is required for Phases 0–9.

[Release inputs](RELEASE.md) · [Quality scope](PHASE-7.md) · [Reliability](PHASE-8.md)
