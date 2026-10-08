# Owner handover and improvement backlog

William owns this synthetic demonstration: access approval, secrets, backups,
budget, release decisions and incident response. No other person or external
notification destination is assumed. The supported setup is the pinned local
stack and reference CLI/MCP/worker in the release manifest.

## Operating cadence

| When | Owner action |
| --- | --- |
| Before each demo | Check API and Odoo health, credentials, tenant scope and unresolved jobs |
| During active demos | Run readiness/queue monitoring; inspect receiver output and task receipts |
| After the session | Inspect unknown/review/dead states, save evidence, stop idle producers; verify cloud deallocation when cloud exists |
| Weekly while actively used | Review unresolved incidents, connector expiry, backup readability, disk use and actual spend |
| Before each release | Check manifest, applicable regressions, migrations, restore/rollback and changed model/prompt evaluation |
| After a failure | Retain IDs, establish final Odoo effect, add a regression and document resolution |

These are owner procedures, not installed recurring automations. Support is
best-effort for a demo, without a production SLA. Permission bypass, wrong-tenant
results, duplicates or uncertain writes require stopping the affected workflow
and review before continuation. A provider-only outage permits deterministic
read/prepare commands if the domain service and source remain healthy.

Retention and access rules are in `LOCAL-RUNBOOK.md`: private data stays outside
Git, unresolved evidence is retained, and purge is manual after backup review.
Public documentation reports the current validated state. Raw private backups
are not distribution artifacts.

## Prioritized backlog

1. Phase 10: confirm subscription, region, budget, access method and recipient;
   implement IaC, HTTPS and private service boundaries, publish immutable images,
   initialize fresh synthetic accounts, then repeat cloud acceptance.
2. Replace shared demo-account passwords before any remote exposure; manage
   credentials per identity. Keep automation limited to its tenant and skills.
3. Implement and verify human alert delivery, encrypted off-host backups,
   automatic deallocation and teardown inventory in the cloud environment.
4. Add a longer soak and host/restart failures after selecting real cloud
   capacity. The Phase 8 two-minute soak is deliberately bounded.
5. Evaluate stronger local models on newly defined cases before offering a
   quality-qualified local-only default. Claude/Grok canaries remain optional.
6. Extend the delivered [browser workspace](WEB-UI.md) only after its cloud
   access controls are verified. Natural-language assistance remains in the CLI.
7. Measure human active time with a real study before claiming time savings
   or financial ROI. Preserve the existing synthetic-performance boundary.
