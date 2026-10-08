"""Explicit migration/seed commands; reset is restricted to the dedicated test DB."""
import argparse
import hashlib
import os
from pathlib import Path
from uuid import UUID

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from pwdlib import PasswordHash

MIGRATIONS = Path(__file__).parent / "migrations"
TENANT_A = UUID("00000000-0000-0000-0000-000000000001")
TENANT_B = UUID("00000000-0000-0000-0000-000000000002")


def admin_connection():
    return psycopg.connect(os.environ["MIGRATION_DATABASE_URL"], connect_timeout=5)


def migrate():
    password = os.environ["APP_DB_PASSWORD"]
    if len(password) < 24:
        raise ValueError("APP_DB_PASSWORD must contain at least 24 characters")
    with admin_connection() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(2026100802)")
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname='odoo_ops_app'").fetchone():
            conn.execute(sql.SQL("CREATE ROLE odoo_ops_app LOGIN PASSWORD {}").format(sql.Literal(password)))
        else:
            conn.execute(sql.SQL("ALTER ROLE odoo_ops_app PASSWORD {}").format(sql.Literal(password)))
        conn.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version text PRIMARY KEY, checksum text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())")
        for path in sorted(MIGRATIONS.glob("*.sql")):
            content = path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(content.encode()).hexdigest()
            previous = conn.execute("SELECT checksum FROM schema_migrations WHERE version=%s", (path.name,)).fetchone()
            if previous:
                if previous[0] != checksum:
                    raise RuntimeError("Applied migration checksum mismatch")
                continue
            conn.execute(content)
            conn.execute("INSERT INTO schema_migrations(version,checksum) VALUES (%s,%s)", (path.name, checksum))
    print("Migrations applied and checksums verified")


def seed():
    if os.environ.get("APP_ENV") not in ("local", "test"):
        raise RuntimeError("Synthetic seed requires APP_ENV=local or test")
    password = os.environ["DEMO_PASSWORD"]
    if len(password) < 16:
        raise ValueError("DEMO_PASSWORD must contain at least 16 characters")
    password_hash = PasswordHash.recommended().hash(password)
    with admin_connection() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(2026100802)")
        for index, tenant in enumerate((TENANT_A, TENANT_B), start=1):
            suffix = "a" if index == 1 else "b"
            conn.execute("INSERT INTO tenants VALUES (%s,%s) ON CONFLICT DO NOTHING", (tenant, f"Demo Company {suffix.upper()}"))
            for role_index, role in enumerate(("operator", "approver", "administrator", "auditor", "worker"), start=1):
                actor = UUID(int=100 * index + role_index)
                conn.execute("INSERT INTO actors(id,tenant_id,username,password_hash,role) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", (actor, tenant, f"{role}.{suffix}", password_hash, role))
            for number in (1, 2):
                customer = UUID(int=1000 * index + number)
                conn.execute("INSERT INTO customers VALUES (%s,%s,%s,%s,'synthetic_local') ON CONFLICT DO NOTHING", (customer, tenant, "Synthetic Nusantara Trading", f"{suffix.upper()}-{number:03d}"))
    print("Synthetic seed ready: two tenants, ten actors, four customers; existing credentials preserved")


def reset_test():
    config = conninfo_to_dict(os.environ["MIGRATION_DATABASE_URL"])
    if os.environ.get("APP_ENV") != "test" or os.environ.get("ALLOW_TEST_RESET") != "yes" or config.get("dbname") != "odoo_ops_test":
        raise RuntimeError("Reset refused: requires test environment, explicit flag and exact odoo_ops_test database")
    with admin_connection() as conn:
        actual = conn.execute("SELECT current_database()").fetchone()[0]
        if actual != "odoo_ops_test":
            raise RuntimeError("Reset refused: database mismatch")
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
    migrate()
    seed()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("migrate", "seed", "reset-test"))
    command = parser.parse_args().command
    try:
        {"migrate": migrate, "seed": seed, "reset-test": reset_test}[command]()
    except Exception as exc:
        # Database exceptions may embed connection data; emit only the class.
        print(f"Management command failed: {type(exc).__name__}; verify environment/database/configuration")
        raise SystemExit(1) from None
