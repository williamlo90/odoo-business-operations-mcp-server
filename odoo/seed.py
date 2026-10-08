"""Executed by Odoo shell only in the named local synthetic database."""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

assert env.cr.dbname == 'odoo_ops_sandbox', 'Refusing non-sandbox database'
path = Path('/run/ops-config/connections.json')
if path.exists() and env['ops.connection'].search_count([]) == 2:
    print('Existing sandbox seed and credentials preserved')
else:
    currency = env.ref('base.IDR')
    currency.active = True
    admin = env.ref('base.user_admin')
    admin.password = os.environ['ODOO_ADMIN_PASSWORD']
    config = {}
    for index, suffix in enumerate(('a', 'b'), start=1):
        tenant = f'00000000-0000-0000-0000-{index:012d}'
        company = env['res.company'].search([('name', '=', 'Ops Demo ' + suffix.upper())], limit=1)
        if not company:
            company = env['res.company'].create({'name': 'Ops Demo ' + suffix.upper(), 'currency_id': currency.id})
        admin.company_ids = [(4, company.id)]
        context = dict(allowed_company_ids=[company.id], tracking_disable=True, mail_create_nosubscribe=True)
        def model(name):
            return env[name].with_context(context).with_company(company)
        plist = model('product.pricelist').search([('name', '=', 'OPS-' + suffix.upper())], limit=1)
        if not plist:
            plist = model('product.pricelist').create({'name': 'OPS-' + suffix.upper(), 'company_id': company.id, 'currency_id': currency.id})
        partners = []
        for number in (1, 2):
            reference = f'OPS-{suffix.upper()}-{number:03d}'
            partner = model('res.partner').search([('ref', '=', reference)], limit=1)
            if not partner:
                partner = model('res.partner').create({'name': 'Synthetic Nusantara Trading', 'ref': reference,
                    'company_id': company.id, 'customer_rank': 1, 'property_product_pricelist': plist.id})
            partners.append(partner)
        for number, price in ((1, 100000 if suffix == 'a' else 120000), (2, 50000)):
            code = f'OPS-{suffix.upper()}-P{number}'
            if not model('product.product').search([('default_code', '=', code)]):
                model('product.product').create({'name': 'Synthetic Service ' + str(number), 'default_code': code,
                    'company_id': company.id, 'type': 'service', 'list_price': price, 'taxes_id': [(5, 0, 0)],
                    'supplier_taxes_id': [(5, 0, 0)]})
        sales = env['res.users'].search([('login', '=', 'ops.sales.' + suffix)], limit=1)
        if not sales:
            sales = env['res.users'].with_context(no_reset_password=True).create({'name': 'Ops Sales ' + suffix,
                'login': 'ops.sales.' + suffix, 'company_id': company.id, 'company_ids': [(6, 0, [company.id])],
                'group_ids': [(6, 0, [env.ref('base.group_user').id, env.ref('sales_team.group_sale_salesman').id])]})
        if not model('crm.lead').search([('name', '=', 'OPS Opportunity ' + suffix.upper())]):
            model('crm.lead').create({'name': 'OPS Opportunity ' + suffix.upper(), 'type': 'opportunity',
                'partner_id': partners[0].id, 'company_id': company.id, 'user_id': sales.id})
        service = env['res.users'].search([('login', '=', 'ops.connector.' + suffix)], limit=1)
        if not service:
            service = env['res.users'].with_context(no_reset_password=True).create({'name': 'Ops Connector ' + suffix,
                'login': 'ops.connector.' + suffix, 'company_id': company.id, 'company_ids': [(6, 0, [company.id])],
                'group_ids': [(6, 0, [env.ref('base.group_portal').id, env.ref('ops_bridge.group_connector').id])]})
        if not env['ops.connection'].search([('tenant', '=', tenant)]):
            env['ops.connection'].create({'tenant': tenant, 'company_id': company.id, 'user_id': service.id, 'pricelist_id': plist.id})
        env['res.users.apikeys'].search([('user_id', '=', service.id), ('name', '=', 'ops-local-v1')]).unlink()
        key = env['res.users.apikeys'].with_user(service).sudo()._generate('rpc', 'ops-local-v1', datetime.now() + timedelta(days=90))
        config[tenant] = {'url': 'http://odoo:8069', 'database': 'odoo_ops_sandbox', 'company_id': company.id, 'api_key': key}
    env.cr.commit()
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(config), encoding='utf-8')
    temporary.replace(path)
    print('Synthetic Odoo sandbox ready: two scoped connections; keys saved to private config')
