CREATE TABLE proposals (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    actor_id uuid NOT NULL,
    kind text NOT NULL CHECK (kind IN ('quote','activity')),
    payload jsonb NOT NULL,
    preview jsonb NOT NULL,
    payload_hash text NOT NULL,
    contract_version text NOT NULL CHECK (contract_version='1.0'),
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    UNIQUE (tenant_id,id),
    FOREIGN KEY (tenant_id,actor_id) REFERENCES actors(tenant_id,id)
);
CREATE TABLE approvals (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    proposal_id uuid UNIQUE NOT NULL,
    approver_id uuid NOT NULL,
    payload_hash text NOT NULL,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id,id),
    FOREIGN KEY (tenant_id,proposal_id) REFERENCES proposals(tenant_id,id),
    FOREIGN KEY (tenant_id,approver_id) REFERENCES actors(tenant_id,id)
);
CREATE TABLE operations (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    proposal_id uuid UNIQUE NOT NULL,
    approval_id uuid NOT NULL,
    idempotency_key uuid NOT NULL,
    envelope jsonb NOT NULL,
    signature text NOT NULL,
    status text NOT NULL CHECK (status IN ('dispatched','unknown','verified','failed','review')),
    result jsonb,
    error_code text,
    attempts integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id,idempotency_key),
    FOREIGN KEY (tenant_id,proposal_id) REFERENCES proposals(tenant_id,id),
    FOREIGN KEY (tenant_id,approval_id) REFERENCES approvals(tenant_id,id)
);
CREATE TABLE business_events (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    actor_id uuid NOT NULL,
    resource_id uuid,
    event text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id,actor_id) REFERENCES actors(tenant_id,id)
);
GRANT SELECT, INSERT ON proposals, approvals, business_events TO odoo_ops_app;
GRANT SELECT, INSERT, UPDATE ON operations TO odoo_ops_app;
