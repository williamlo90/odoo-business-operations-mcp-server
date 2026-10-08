# Azure proposal — not provisioned

Phase 9 prepares this design; Phase 10 implements and validates infrastructure.
`deploy/azure/plan.json` is a reviewable proposal, not a deployment template.
No Azure resources were created. The target is a restricted synthetic demo.

## Topology

Start with one Linux VM, proposed `Standard_B2ls_v2` (2 vCPU / 4 GiB) in Southeast
Asia, in a dedicated resource group. Run API, Odoo and their separate PostgreSQL
containers, preserving the tested Compose topology. Use durable managed storage
for databases and filestore. Regional availability, burst credits and actual
cloud performance must be verified. This single VM has no high availability.
The proposed B2ls v2 specification is listed in the
[Bsv2 size table](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/general-purpose/bsv2-series).

Run the reference CLI, MCP subprocess and worker on the VM. Their existing
loopback HTTP allowlist stays intact. Hosted inference uses outbound HTTPS;
Ollama/GPU hosting is excluded from the initial design and estimate.

| Boundary | Proposed access |
| --- | --- |
| Browser workspace and Odoo | HTTPS 443 through a reverse proxy, separate hostnames, named accounts, owner-approved domain and source-IP restrictions |
| Administration | SSH keys from the owner's CIDR only; no unrestricted port 22 |
| API | Loopback 8020; VM-local client or an approved SSH tunnel; no public 8020 |
| Odoo | Loopback 8069 behind HTTPS; no public 8069 |
| PostgreSQL | Private Docker networks; no published database ports |
| MCP | Authenticated stdio processes; no public MCP listener |

The Phase 9A browser workspace is served by the API container at its root.
Proxy a restricted HTTPS workspace hostname to loopback 8020 and a separate
Odoo hostname to loopback 8069. Natural-language assistant operation remains
through the CLI. Before remote exposure, replace shared
demo-account passwords with distinct credentials and repeat role tests. Initialize
fresh synthetic cloud records rather than copying local secrets or databases.

## Identity, data and recovery

Give the VM a managed identity with only project-vault secret-read and access to
its specific private backup container. Deployment permissions are separate from
runtime and business roles; avoid subscription-wide runtime privileges. Managed
identity credentials are managed by Azure. [Identity guidance](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/managed-identity-best-practice-recommendations).

Phase 10 bootstrap must retrieve only required keys, write restricted runtime
files and avoid logging values. No credentials belong in image layers, committed
IaC parameters or demo recordings. Treat trusted processes on the VM as sharing
the managed-identity security boundary; restrict untrusted container access.

Use managed storage rather than temporary VM disks. Keep encrypted private
backup objects off the VM with TLS and identity-based access. Proposed retention:
seven daily and four weekly matching database/filestore/SQLite backups. Restore
into an isolated target before relying on them. Disk snapshots alone do not
prove consistency across both databases and the Odoo filestore. Cloud RPO/RTO
will be selected after actual recovery measurements.

## Cost proposal

The Azure Retail Prices API returned **US$0.0528/hour** for Linux B2ls v2 consumption
in Southeast Asia on 2026-10-08. The meter/filter are captured in
[pricing evidence](evidence/phase9-pricing.json).
[Retail Prices API](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices).

| Scenario | Compute | Other-service allowance | Illustrative Azure subtotal |
| --- | --- | --- | --- |
| 50 running hours/month | $2.64 | $15–25/month | $17.64–27.64/month |
| 730 running hours/month | $38.54 | $15–25/month | $53.54–63.54/month |

The allowance is an engineering reserve, not a provider quote. It covers proposed
OS/data disks, IP, backup storage, secrets, registry and light monitoring. Price
the final resource inventory in the selected account before provisioning. Taxes,
exchange rates, substantial egress/logging and model charges are excluded. No
free-tier eligibility or account discount is assumed.

Propose **$30/month Azure for limited demo hours**, plus a separate **$5/month
model envelope**. Neither is approved or configured. Always-on operation needs
a different budget. Restrict VM size/count and container resources, limit log
ingestion, set an approved automatic deallocation schedule and verify the VM's
deallocated state after demos. Guest shutdown alone is insufficient; retained
disks and other resources may still cost money.
[VM pricing](https://azure.microsoft.com/en-us/pricing/details/virtual-machines/linux/).

Budget thresholds at 50/80/100 percent and forecast send notifications; they are
not a hard spending cap. Cost data and evaluation are delayed. Deallocation and
owner checks remain necessary.
[Budget behavior](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets).

## Phase 10 gates

1. Confirm subscription, region/quota, owner CIDR, domain/access, budget, demo
   hours and alert recipient. Resolve unset values in `deploy/azure/plan.json`.
2. Implement versioned Bicep/Terraform for the dedicated group, network, VM/disks,
   identity, secret store, backups, monitor and budget. Validate a concrete
   what-if/plan and priced inventory before applying it.
3. Publish tested images to a private registry; record immutable registry
   digests and source provenance. Local image IDs are not registry digests.
   Bootstrap pinned dependencies, new credentials, migrations and synthetic data.
4. Configure HTTPS and restricted access before a remote demo. Test external
   role/tenant denials and verify internal ports are unreachable publicly.
5. Repeat business correctness, concurrency, normal/peak/soak and unknown-write
   tests on cloud identities. Adapt local-only test harnesses with explicit
   cloud-target safeguards; do not relabel local evidence as cloud validation.
6. Implement readiness, disk, queue age, unresolved-operation and failed-backup
   alerts using an action group with an approved recipient. Trigger an incident
   and prove receipt/recovery. The current SQLite receiver is not human paging.
7. Verify off-host backup, isolated restore, read-back and compatible image
   rollback. Publish cloud evidence, access instructions and actual costs only
   after these gates pass.

## Shutdown and teardown

Stop producers and deallocate the exact project VM after each session; verify
power state and retained disks/IP/storage. For full teardown, verify the desired
backup first, enumerate exact project resource IDs and review their deletion
plan. Never perform subscription-wide cleanup or remove shared resources.
Include retained backups and soft-deleted resources in the final inventory and
cost review. No deletion command uses inferred subscription or resource names.

Keeping the project local-only remains possible: label it local-delivered and
cloud-pending without changing the verified local results.
