import os
import subprocess
import sys
import tempfile
from pathlib import Path

mode = sys.argv[1]
config = ('[options]\ndb_host=odoo-db\ndb_port=5432\ndb_user=odoo\n'
          f'db_password={os.environ["ODOO_DB_PASSWORD"]}\n'
          f'admin_passwd={os.environ["ODOO_ADMIN_PASSWORD"]}\n'
          'db_name=odoo_ops_sandbox\ndbfilter=^odoo_ops_sandbox$\nlist_db=False\n'
          'addons_path=/usr/lib/python3/dist-packages/odoo/addons,/opt/ops-addons\n'
          'data_dir=/var/lib/odoo\nmax_cron_threads=0\nworkers=0\n'
          'log_level=warn\nlog_handler=werkzeug:ERROR\n')
with tempfile.NamedTemporaryFile('w', suffix='.conf', delete=False) as file:
    file.write(config)
    filename = file.name
try:
    if mode == 'seed':
        result = subprocess.run(['odoo', 'shell', '-c', filename, '--no-http'],
                                input=Path('/opt/ops/seed.py').read_text(), text=True)
    elif mode == 'init':
        result = subprocess.run(['odoo', '-c', filename, '-i', 'ops_bridge', '--without-demo', '--stop-after-init', '--no-http'])
    elif mode == 'upgrade':
        result = subprocess.run(['odoo', '-c', filename, '-u', 'ops_bridge', '--stop-after-init', '--no-http'])
    elif mode == 'serve':
        result = subprocess.run(['odoo', '-c', filename])
    else:
        raise ValueError('Unknown mode')
    sys.exit(result.returncode)
finally:
    Path(filename).unlink(missing_ok=True)
