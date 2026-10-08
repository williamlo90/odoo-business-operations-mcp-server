# Business skills

Four executable packages share `backend.assistant.skills.execute_skill`:

- [research_customer](research_customer/SKILL.md)
- [prepare_quote](prepare_quote/SKILL.md)
- [prepare_crm_activity](prepare_crm_activity/SKILL.md)
- [reconcile_odoo_write](reconcile_odoo_write/SKILL.md)

Each package includes versioned input/output schemas and a binding manifest.
These are application capabilities, not installed Codex skills. The assistant and
direct skill caller use the same handler and authenticated Phase 2 HTTP gateway.
Automation worker integration remains Phase 5 work. Current validation uses
simulated HTTP transports; live Phase 3 validation remains pending.

See [Phase 3 progress and setup](../docs/PHASE-3.md).
