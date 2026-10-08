# Business skills

Four executable packages share `backend.assistant.skills.execute_skill`:

- [research_customer](research_customer/SKILL.md)
- [prepare_quote](prepare_quote/SKILL.md)
- [prepare_crm_activity](prepare_crm_activity/SKILL.md)
- [reconcile_odoo_write](reconcile_odoo_write/SKILL.md)

Each package includes versioned input/output schemas and a binding manifest.
These are application capabilities, not installed Codex skills. The assistant and
worker call the same handler through authenticated HTTP or MCP gateways.
Phase 5 validates reuse, persistent jobs and tenant isolation with simulated domain
HTTP; live Odoo/provider acceptance is Phase 6.

See [assistant setup](../docs/PHASE-3.md) and [worker setup](../docs/PHASE-5.md).
