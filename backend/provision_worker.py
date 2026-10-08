"""Provision a dedicated synthetic operator account; never elevate the worker role."""
import os
from uuid import NAMESPACE_URL, uuid5

from pwdlib import PasswordHash

from backend.manage import admin_connection, TENANT_A, TENANT_B


def provision():
    suffix=os.environ.get('WORKER_TENANT_SUFFIX')
    password=os.environ.get('WORKER_PASSWORD','')
    if os.environ.get('APP_ENV')!='local' or suffix not in {'a','b'} or len(password)<24:
        raise ValueError('invalid_worker_provisioning_configuration')
    username='automation.'+suffix
    tenant=TENANT_A if suffix=='a' else TENANT_B
    actor=uuid5(NAMESPACE_URL,'odoo-ops-local:'+username)
    hasher=PasswordHash.recommended()
    with admin_connection() as conn:
        if conn.execute('SELECT current_database()').fetchone()[0]!='odoo_ops_local':
            raise ValueError('synthetic_local_database_required')
        conn.execute('SELECT pg_advisory_xact_lock(2026100802)')
        existing=conn.execute('SELECT id,tenant_id,password_hash,role,active FROM actors WHERE username=%s',(username,)).fetchone()
        if existing:
            if existing[0]!=actor or existing[1]!=tenant or existing[3:]!=('operator',True) or not hasher.verify(password,existing[2]):
                raise ValueError('existing_worker_identity_mismatch')
        else:
            conn.execute('INSERT INTO actors(id,tenant_id,username,password_hash,role) VALUES (%s,%s,%s,%s,%s)',
                (actor,tenant,username,hasher.hash(password),'operator'))
    print('Dedicated synthetic automation operator ready; existing credentials preserved.')


if __name__=='__main__':
    try:
        provision()
    except Exception:
        raise SystemExit('worker_provisioning_failed; verify local configuration and database') from None
