"""Extend local config without replacing existing credentials."""
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / ".env"
existing = path.read_text()
keys = {line.partition('=')[0] for line in existing.splitlines()}
with path.open('a', encoding='utf-8') as stream:
    for name in ('ODOO_DB_PASSWORD', 'ODOO_ADMIN_PASSWORD', 'OPS_SIGNING_KEY'):
        if name not in keys:
            stream.write(f'\n{name}={secrets.token_hex(32)}\n')
(root / 'local' / 'odoo-config').mkdir(parents=True, exist_ok=True)
print('Odoo local secret configuration ready; existing values preserved')
