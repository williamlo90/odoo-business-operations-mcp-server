CREATE TABLE tenants (
    id uuid PRIMARY KEY,
    name text NOT NULL
);
CREATE TABLE actors (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    username text UNIQUE NOT NULL,
    password_hash text NOT NULL,
    role text NOT NULL CHECK (role IN ('operator','approver','administrator','auditor','worker')),
    active boolean NOT NULL DEFAULT true,
    UNIQUE (tenant_id, id)
);
CREATE TABLE sessions (
    token_hash text PRIMARY KEY,
    actor_id uuid NOT NULL REFERENCES actors(id),
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX sessions_actor_idx ON sessions(actor_id);
CREATE TABLE login_attempts (
    bucket text PRIMARY KEY,
    attempts integer NOT NULL,
    window_start timestamptz NOT NULL
);
CREATE TABLE customers (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    name text NOT NULL,
    reference text NOT NULL,
    source text NOT NULL CHECK (source = 'synthetic_local'),
    UNIQUE (tenant_id, id),
    UNIQUE (tenant_id, reference)
);
CREATE INDEX customers_tenant_idx ON customers(tenant_id, id);
CREATE TABLE work_requests (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    actor_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    intent text NOT NULL CHECK (intent = 'research_customer'),
    status text NOT NULL CHECK (status = 'recorded_local'),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id, actor_id) REFERENCES actors(tenant_id, id),
    FOREIGN KEY (tenant_id, customer_id) REFERENCES customers(tenant_id, id)
);
CREATE INDEX work_requests_tenant_idx ON work_requests(tenant_id, id);
CREATE TABLE audit_events (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    actor_id uuid NOT NULL,
    action text NOT NULL CHECK (action = 'work_request.recorded'),
    resource_id uuid NOT NULL REFERENCES work_requests(id),
    correlation_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id, actor_id) REFERENCES actors(tenant_id, id)
);
GRANT USAGE ON SCHEMA public TO odoo_ops_app;
GRANT SELECT ON tenants, actors, customers, schema_migrations TO odoo_ops_app;
GRANT SELECT, INSERT, DELETE ON sessions TO odoo_ops_app;
GRANT SELECT, INSERT, UPDATE ON login_attempts TO odoo_ops_app;
GRANT SELECT, INSERT ON work_requests, audit_events TO odoo_ops_app;
