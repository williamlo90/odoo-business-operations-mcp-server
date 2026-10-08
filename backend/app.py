import hashlib
import json
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID, uuid4

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from pwdlib import PasswordHash

from backend.config import settings
from backend.db import connection
from backend.odoo_adapter import PlatformError
from backend.business import build_router

app = FastAPI(title="Odoo Operations", version="0.2.0")
log = logging.getLogger("operations")
log.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(message)s"))
log.addHandler(handler)
log.propagate = False
passwords = PasswordHash.recommended()
DUMMY_HASH = passwords.hash(secrets.token_urlsafe(32))
bearer = HTTPBearer(auto_error=False)


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9._-]+$")
    password: str = Field(min_length=1, max_length=256)


class WorkRequestInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_id: UUID
    intent: Literal["research_customer"] = "research_customer"


def fail(status: int, code: str):
    raise HTTPException(status_code=status, detail=code)


@app.middleware("http")
async def request_log(request: Request, call_next):
    # Never trust user-supplied IDs or log URLs, bodies, cookies, tokens, usernames.
    correlation = str(uuid4())
    request.state.correlation_id = correlation
    started = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        response = JSONResponse(status_code=500, content={"error": "internal_error"})
    route = request.scope.get("route")
    log.info(json.dumps({"event": "http_request", "correlation_id": correlation,
                         "route": route.path if route else "unmatched",
                         "method": request.method if request.method in {"GET", "POST", "DELETE", "PUT", "PATCH", "OPTIONS", "HEAD"} else "OTHER",
                         "status": response.status_code,
                         "duration_ms": round((time.monotonic() - started) * 1000, 2)}))
    response.headers["X-Correlation-ID"] = correlation
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail},
                        headers={"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # FastAPI default validation responses echo input (including passwords).
    return JSONResponse(status_code=422, content={"error": "invalid_input"})


@app.exception_handler(psycopg.Error)
async def database_error(request: Request, exc: psycopg.Error):
    return JSONResponse(status_code=503, content={"error": "database_unavailable"})


@app.exception_handler(PlatformError)
async def platform_error(request: Request, exc: PlatformError):
    status = 404 if exc.code == 'record_not_found' else 409 if exc.code in {
        'stale_proposal', 'source_changed', 'approval_expired', 'idempotency_conflict'} else 422 if exc.code in {
        'invalid_input', 'invalid_assignee', 'unsupported_pricing', 'unsupported_product'} else 503
    return JSONResponse(status_code=status, content={'error': exc.code})


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def actor(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    if not credentials or len(credentials.credentials) > 256:
        fail(401, "authentication_required")
    with connection() as conn:
        row = conn.execute("""SELECT a.id, a.tenant_id, a.username, a.role FROM actors a
            JOIN sessions s ON s.actor_id=a.id
            WHERE s.token_hash=%s AND s.expires_at > now() AND a.active=true""",
                           (token_digest(credentials.credentials),)).fetchone()
    if not row:
        fail(401, "invalid_session")
    return row


def reader(current=Depends(actor)):
    if current["role"] not in {"operator", "approver", "auditor"}:
        fail(403, "role_not_permitted")
    return current


def operator(current=Depends(actor)):
    if current["role"] != "operator":
        fail(403, "role_not_permitted")
    return current


@app.get("/health/live")
def live():
    return {"status": "alive"}


@app.get("/health/ready")
def ready():
    with connection() as conn:
        applied = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
        if [row["version"] for row in applied] != ["001_foundation.sql", "002_business_workflow.sql"]:
            fail(503, "schema_not_ready")
        conn.execute("SELECT id FROM actors LIMIT 1")
    return {"status": "ready", "schema_version": "002"}


@app.post("/auth/login")
def login(data: Login):
    bucket = token_digest(data.username)
    with connection() as conn:
        # A separate committed transaction preserves failed attempts.
        attempts = conn.execute("""INSERT INTO login_attempts VALUES (%s,1,now())
            ON CONFLICT (bucket) DO UPDATE SET
            attempts=CASE WHEN login_attempts.window_start < now()-interval '1 minute' THEN 1 ELSE login_attempts.attempts+1 END,
            window_start=CASE WHEN login_attempts.window_start < now()-interval '1 minute' THEN now() ELSE login_attempts.window_start END
            RETURNING attempts""", (bucket,)).fetchone()["attempts"]
    if attempts > settings.login_limit:
        fail(429, "login_rate_limited")
    with connection() as conn:
        user = conn.execute("SELECT * FROM actors WHERE username=%s", (data.username,)).fetchone()
        valid = passwords.verify(data.password, user["password_hash"] if user else DUMMY_HASH)
        if not valid or not user or not user["active"]:
            fail(401, "invalid_credentials")
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(minutes=settings.session_minutes)
        conn.execute("DELETE FROM sessions WHERE expires_at <= now()")
        conn.execute("INSERT INTO sessions(token_hash,actor_id,expires_at) VALUES (%s,%s,%s)",
                     (token_digest(token), user["id"], expires))
    return {"access_token": token, "token_type": "bearer", "expires_at": expires}


@app.post("/auth/logout", status_code=204)
def logout(credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)], current=Depends(actor)):
    with connection() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash=%s", (token_digest(credentials.credentials),))


@app.get("/me")
def me(current=Depends(actor)):
    return current


@app.get("/customers")
def customers(current=Depends(reader), limit: Annotated[int, Query(ge=1, le=100)] = 20,
              after: UUID | None = None):
    with connection() as conn:
        rows = conn.execute("""SELECT id,name,reference,source FROM customers
            WHERE tenant_id=%s AND id>%s ORDER BY id LIMIT %s""",
                            (current["tenant_id"], after or UUID(int=0), limit + 1)).fetchall()
    return {"items": rows[:limit], "next_cursor": str(rows[limit - 1]["id"]) if len(rows) > limit else None}


@app.post("/work-requests", status_code=201)
def create_work(data: WorkRequestInput, request: Request, current=Depends(operator)):
    with connection() as conn:
        customer = conn.execute("SELECT id FROM customers WHERE id=%s AND tenant_id=%s",
                                (data.customer_id, current["tenant_id"])).fetchone()
        if not customer:
            fail(404, "customer_not_found")
        work = conn.execute("""INSERT INTO work_requests(id,tenant_id,actor_id,customer_id,intent,status)
            VALUES (%s,%s,%s,%s,%s,'recorded_local') RETURNING *""",
                            (uuid4(), current["tenant_id"], current["id"], data.customer_id, data.intent)).fetchone()
        conn.execute("""INSERT INTO audit_events(id,tenant_id,actor_id,action,resource_id,correlation_id)
            VALUES (%s,%s,%s,'work_request.recorded',%s,%s)""",
                     (uuid4(), current["tenant_id"], current["id"], work["id"], request.state.correlation_id))
    return work


@app.get("/work-requests/{work_id}")
def get_work(work_id: UUID, current=Depends(reader)):
    with connection() as conn:
        work = conn.execute("SELECT * FROM work_requests WHERE id=%s AND tenant_id=%s",
                            (work_id, current["tenant_id"])).fetchone()
    if not work:
        fail(404, "work_request_not_found")
    return work


app.include_router(build_router(actor, reader, operator))
