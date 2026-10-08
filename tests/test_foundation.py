import hashlib
import json
import os
from uuid import UUID

import psycopg
import pytest

from backend.manage import admin_connection, migrate, reset_test, seed


def test_health_and_unauthenticated_denial(api):
    assert api.get("/health/live").json() == {"status": "alive"}
    assert api.get("/health/ready").status_code == 200
    assert api.get("/customers").status_code == 401
    assert api.get("/me", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_persisted_flow_and_audit(api, login):
    headers = login()
    me = api.get("/me", headers=headers).json()
    customers = api.get("/customers", headers=headers).json()["items"]
    assert len(customers) == 2
    assert all(item["reference"].startswith("A-") for item in customers)
    response = api.post("/work-requests", headers=headers, json={"customer_id": customers[0]["id"]})
    assert response.status_code == 201
    work = response.json()
    assert work["tenant_id"] == me["tenant_id"] and work["actor_id"] == me["id"]
    assert work["status"] == "recorded_local"
    assert api.get(f"/work-requests/{work['id']}", headers=headers).json() == work
    with admin_connection() as conn:
        audit = conn.execute("SELECT correlation_id FROM audit_events WHERE resource_id=%s", (work["id"],)).fetchall()
        assert audit == [(UUID(response.headers["X-Correlation-ID"]),)]


def test_cross_tenant_read_write_and_forged_scope(api, login):
    a, b = login(), login("operator.b")
    customer_b = api.get("/customers", headers=b).json()["items"][0]
    customer_a = api.get("/customers", headers=a).json()["items"][0]
    assert api.post("/work-requests", headers=a, json={"customer_id": customer_b["id"]}).status_code == 404
    assert api.post("/work-requests", headers=a, json={"customer_id": customer_a["id"], "tenant_id": str(UUID(int=2))}).status_code == 422
    spoofed = api.get("/customers", headers={**a, "X-Tenant-ID": str(UUID(int=2)), "X-Role": "administrator"}).json()
    assert all(item["reference"].startswith("A-") for item in spoofed["items"])
    work_b = api.post("/work-requests", headers=b, json={"customer_id": customer_b["id"]}).json()
    assert api.get(f"/work-requests/{work_b['id']}", headers=a).status_code == 404


@pytest.mark.parametrize("role", ["approver", "administrator", "auditor", "worker"])
def test_non_operator_cannot_create(api, login, role):
    headers = login(f"{role}.a")
    assert api.post("/work-requests", headers=headers, json={"customer_id": str(UUID(int=1001))}).status_code == 403
    assert api.get("/customers", headers=headers).status_code == (200 if role in {"approver", "auditor"} else 403)


def test_logout_expiry_and_revocation(api, login):
    headers = login()
    assert api.post("/auth/logout", headers=headers).status_code == 204
    assert api.get("/me", headers=headers).status_code == 401
    headers = login()
    digest = hashlib.sha256(headers["Authorization"].split()[1].encode()).hexdigest()
    with admin_connection() as conn:
        conn.execute("UPDATE sessions SET expires_at=now()-interval '1 second' WHERE token_hash=%s", (digest,))
    assert api.get("/me", headers=headers).status_code == 401
    headers = login()
    with admin_connection() as conn:
        conn.execute("UPDATE actors SET active=false WHERE username='operator.a'")
    try:
        assert api.get("/me", headers=headers).status_code == 401
    finally:
        with admin_connection() as conn:
            conn.execute("UPDATE actors SET active=true WHERE username='operator.a'")


def test_role_is_loaded_from_database_each_request(api, login):
    headers = login()
    with admin_connection() as conn:
        conn.execute("UPDATE actors SET role='auditor' WHERE username='operator.a'")
    try:
        assert api.post("/work-requests", headers=headers, json={"customer_id": str(UUID(int=1001))}).status_code == 403
    finally:
        with admin_connection() as conn:
            conn.execute("UPDATE actors SET role='operator' WHERE username='operator.a'")


def test_pagination_and_input_validation(api, login):
    headers = login()
    page1 = api.get("/customers?limit=1", headers=headers).json()
    page2 = api.get("/customers", params={"limit": 1, "after": page1["next_cursor"]}, headers=headers).json()
    assert page1["items"][0]["id"] != page2["items"][0]["id"] and page2["next_cursor"] is None
    assert api.get("/customers?limit=101", headers=headers).status_code == 422
    assert api.post("/work-requests", headers=headers, json={"customer_id": "invalid"}).status_code == 422


def test_invalid_login_and_rate_limit(api):
    assert api.post("/auth/login", json={"username": "missing", "password": "wrong"}).status_code == 401
    bucket = hashlib.sha256(b"limited").hexdigest()
    with admin_connection() as conn:
        conn.execute("INSERT INTO login_attempts VALUES (%s,100,now())", (bucket,))
    assert api.post("/auth/login", json={"username": "limited", "password": "wrong"}).status_code == 429


def test_logs_and_errors_do_not_echo_secrets(api, login, server):
    marker = "PRIVATE-INPUT-MARKER"
    response = api.post("/auth/login", json={"username": "operator.a", "password": marker, "unexpected": marker})
    assert response.status_code == 422 and marker not in response.text
    headers = login()
    api.get(f"/unknown/{marker}?secret={marker}", headers={**headers, "X-Correlation-ID": marker})
    logs = server["log"].read_text()
    for value in (marker, os.environ["DEMO_PASSWORD"], os.environ["APP_DB_PASSWORD"], headers["Authorization"].split()[1]):
        assert value not in logs
    events = [json.loads(line) for line in logs.splitlines() if line.startswith('{')]
    assert events and all(set(event) == {"event", "correlation_id", "route", "method", "status", "duration_ms"} for event in events)


def test_database_constraints_and_runtime_privilege(api):
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        assert conn.execute("SELECT rolsuper FROM pg_roles WHERE rolname=current_user").fetchone() == (False,)
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("CREATE TABLE forbidden (id integer)")
    with admin_connection() as conn:
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            conn.execute("INSERT INTO work_requests VALUES (%s,%s,%s,%s,'research_customer','recorded_local',now())", (UUID(int=99999), UUID(int=1), UUID(int=101), UUID(int=2001)))


def test_migrations_and_seed_are_repeatable(api):
    with admin_connection() as conn:
        before = conn.execute("SELECT count(*) FROM work_requests").fetchone()
    migrate()
    seed()
    with admin_connection() as conn:
        assert conn.execute("SELECT count(*) FROM customers").fetchone() == (4,)
        assert conn.execute("SELECT count(*) FROM actors").fetchone() == (10,)
        assert conn.execute("SELECT count(*) FROM work_requests").fetchone() == before
        hashed = conn.execute("SELECT password_hash FROM actors LIMIT 1").fetchone()[0]
        assert hashed.startswith('$argon2') and hashed != os.environ["DEMO_PASSWORD"]


def test_test_reset_refuses_local_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    with pytest.raises(RuntimeError, match="Reset refused"):
        reset_test()


def test_test_reset_refuses_non_test_database(monkeypatch):
    monkeypatch.setenv("MIGRATION_DATABASE_URL", "postgresql://x:x@localhost/odoo_ops_local")
    with pytest.raises(RuntimeError, match="Reset refused"):
        reset_test()


def test_configuration_rejects_invalid_settings(monkeypatch):
    from backend.config import Settings
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite:///local.db")
    with pytest.raises(ValidationError):
        Settings(session_minutes=0)
