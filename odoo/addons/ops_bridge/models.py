"""Narrow JSON-2 facade. Sudo is confined to explicitly scoped business operations.

Each execute and its deduplication ledger entry commit in one Odoo transaction.
V1 serializes source-table writes during execution: conservative, local-scale policy.
"""
import hashlib
import hmac
import json
import os
import time
from datetime import date
from decimal import Decimal
from uuid import UUID

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def invalid(code):
    raise ValidationError("OPS:" + code)


class Connection(models.Model):
    _name = "ops.connection"
    _description = "Operations company binding"
    tenant = fields.Char(required=True)
    company_id = fields.Many2one("res.company", required=True)
    user_id = fields.Many2one("res.users", required=True)
    pricelist_id = fields.Many2one("product.pricelist", required=True)
    _tenant_unique = models.Constraint("UNIQUE(tenant)", "Tenant binding already exists")
    _user_unique = models.Constraint("UNIQUE(user_id)", "Connector user already bound")


class Operation(models.Model):
    _name = "ops.operation"
    _description = "Atomic operations receipt"
    operation_id = fields.Char(required=True, index=True)
    company_id = fields.Many2one("res.company", required=True)
    payload_hash = fields.Char(required=True)
    kind = fields.Selection([("quote", "Quotation"), ("activity", "Activity")], required=True)
    external_id = fields.Integer(required=True)
    _operation_unique = models.Constraint("UNIQUE(operation_id)", "Operation already exists")


class Bridge(models.AbstractModel):
    _name = "ops.bridge"
    _description = "Approved Operations API v1"

    def _binding(self):
        if not self.env.user.has_group("ops_bridge.group_connector"):
            raise AccessError("OPS:forbidden")
        binding = self.env["ops.connection"].sudo().search([("user_id", "=", self.env.uid)], limit=1)
        if not binding or not self.env.user.active:
            raise AccessError("OPS:forbidden")
        return binding

    def _model(self, name, binding):
        # Drop all caller-provided context, especially company/default overrides.
        return self.env[name].sudo().with_context({"allowed_company_ids": [binding.company_id.id],
            "tracking_disable": True, "mail_create_nosubscribe": True,
            "mail_notify_force_send": False, "mail_activity_quick_update": True,
            "lang": "en_US"}).with_company(binding.company_id)

    def _record(self, model, record_id, binding):
        if type(record_id) is not int or record_id < 1:
            invalid("invalid_input")
        record = self._model(model, binding).search([("id", "=", record_id), ("company_id", "=", binding.company_id.id)], limit=1)
        if not record:
            invalid("record_not_found")
        return record

    @api.model
    def info(self):
        binding = self._binding()
        return {"contract_version": "1.0", "tenant": binding.tenant,
                "company_id": binding.company_id.id, "edition": "Community", "api": "JSON-2"}

    @api.model
    def customers(self, query="", after=0, limit=20, revision=None):
        b = self._binding()
        if not isinstance(query, str) or len(query) > 100 or type(after) is not int or after < 0 or type(limit) is not int or not 1 <= limit <= 100:
            invalid("invalid_input")
        model = self._model("res.partner", b)
        domain = [("company_id", "=", b.company_id.id), ("customer_rank", ">", 0)]
        # Detect changed pagination source without returning other-company records.
        records = model.search(domain, order="id", limit=1001)
        if len(records) > 1000:
            invalid("catalog_limit")
        current_revision = fingerprint([(r.id, str(r.write_date)) for r in records])
        if revision is not None and revision != current_revision:
            invalid("source_changed")
        matching = records.filtered(lambda r: query.lower() in r.name.lower() or query.lower() in (r.ref or "").lower())
        page = matching.filtered(lambda r: r.id > after)[:limit + 1]
        return {"items": [{"id": r.id, "name": r.name, "reference": r.ref, "company_id": b.company_id.id,
                           "source": "odoo:res.partner", "version": str(r.write_date)} for r in page[:limit]],
                "next_cursor": page[limit - 1].id if len(page) > limit else None,
                "revision": current_revision, "ambiguous": len(matching) > 1}

    @api.model
    def catalog(self):
        b = self._binding()
        products = self._model("product.product", b).search([("company_id", "=", b.company_id.id), ("sale_ok", "=", True)], order="id", limit=101)
        if len(products) > 100:
            invalid("catalog_limit")
        return {"items": [{"id": p.id, "code": p.default_code, "name": p.name,
                           "unit_price": str(p.lst_price)} for p in products],
                "currency": b.pricelist_id.currency_id.name, "pricing_policy": "list-price-no-tax-v1"}

    @api.model
    def opportunities(self):
        b = self._binding()
        records = self._model("crm.lead", b).search([("company_id", "=", b.company_id.id), ("type", "=", "opportunity")], order="id", limit=101)
        if len(records) > 100:
            invalid("catalog_limit")
        return {"items": [self._opportunity(r) for r in records]}

    def _opportunity(self, record):
        return {"id": record.id, "company_id": record.company_id.id, "name": record.name,
                "customer_id": record.partner_id.id, "owner_id": record.user_id.id,
                "stage": record.stage_id.name, "version": str(record.write_date), "source": "odoo:crm.lead"}

    @api.model
    def opportunity(self, opportunity_id):
        b = self._binding()
        return self._opportunity(self._record("crm.lead", opportunity_id, b))

    def _preview(self, kind, payload, b):
        if not isinstance(payload, dict):
            invalid("invalid_input")
        versions = {"company": str(b.company_id.write_date), "binding": str(b.write_date)}
        if kind == "quote":
            if set(payload) != {"customer_id", "items"} or not isinstance(payload["items"], list) or not 1 <= len(payload["items"]) <= 20:
                invalid("invalid_input")
            partner = self._record("res.partner", payload["customer_id"], b)
            pricelist = b.pricelist_id
            currency = pricelist.currency_id
            if (pricelist.company_id != b.company_id or not pricelist.active or not currency.active
                    or currency.name != "IDR" or currency != b.company_id.currency_id
                    or pricelist.item_ids or partner.property_account_position_id):
                invalid("unsupported_pricing")
            versions.update({"customer": str(partner.write_date), "pricelist": str(pricelist.write_date),
                             "currency": str(currency.write_date), "currency_rounding": str(currency.rounding)})
            lines, seen = [], set()
            for item in payload["items"]:
                if not isinstance(item, dict) or set(item) != {"product_id", "quantity"}:
                    invalid("invalid_input")
                product = self._record("product.product", item["product_id"], b)
                quantity = item["quantity"]
                if type(quantity) is not int or not 1 <= quantity <= 1000 or product.id in seen:
                    invalid("invalid_input")
                if not product.active or not product.sale_ok or product.taxes_id:
                    invalid("unsupported_product")
                price = Decimal(str(product.lst_price))
                if price < 0 or price != price.to_integral_value():
                    invalid("unsupported_pricing")
                seen.add(product.id)
                versions[str(product.id)] = [str(product.write_date), str(product.product_tmpl_id.write_date),
                                             str(product.uom_id.write_date)]
                lines.append({"product_id": product.id, "name": product.name, "quantity": quantity,
                              "unit_price": str(price), "subtotal": str(price * quantity)})
            result = {"kind": kind, "company_id": b.company_id.id, "customer_id": partner.id,
                      "customer_name": partner.name, "currency": "IDR", "pricelist_id": pricelist.id,
                      "pricing_policy": "list-price-no-tax-v1", "items": lines,
                      "total": str(sum(Decimal(line["subtotal"]) for line in lines))}
        elif kind == "activity":
            if set(payload) != {"opportunity_id", "assignee_id", "due_date", "summary"}:
                invalid("invalid_input")
            lead = self._record("crm.lead", payload["opportunity_id"], b)
            user = self._model("res.users", b).browse(payload["assignee_id"]).exists()
            if not user or not user.active or user.share or b.company_id not in user.company_ids:
                invalid("invalid_assignee")
            try:
                due = date.fromisoformat(payload["due_date"])
            except (ValueError, TypeError):
                invalid("invalid_input")
            summary = payload["summary"]
            if not isinstance(summary, str) or not 1 <= len(summary.strip()) <= 120 or '<' in summary or '>' in summary:
                invalid("invalid_input")
            versions.update({"lead": str(lead.write_date), "assignee": str(user.write_date)})
            result = {"kind": kind, "company_id": b.company_id.id, "opportunity_id": lead.id,
                      "assignee_id": user.id, "due_date": due.isoformat(), "summary": summary}
        else:
            invalid("invalid_kind")
        result["source_version"] = fingerprint({"values": result, "versions": versions})
        result["contract_version"] = "1.0"
        return result

    @api.model
    def prepare(self, kind, payload):
        return self._preview(kind, payload, self._binding())

    def _receipt(self, ledger, b):
        if ledger.kind == "quote":
            order = self._record("sale.order", ledger.external_id, b)
            value = {"kind": "quote", "external_id": order.id, "name": order.name, "state": order.state,
                     "company_id": order.company_id.id, "customer_id": order.partner_id.id,
                     "currency": order.currency_id.name, "total": str(order.amount_total),
                     "items": [{"product_id": line.product_id.id, "quantity": line.product_uom_qty,
                                "unit_price": str(line.price_unit), "subtotal": str(line.price_subtotal)}
                               for line in order.order_line]}
        else:
            activity = self._model("mail.activity", b).browse(ledger.external_id).exists()
            if not activity:
                invalid("record_not_found")
            self._record("crm.lead", activity.res_id, b)
            value = {"kind": "activity", "external_id": activity.id, "company_id": b.company_id.id,
                     "opportunity_id": activity.res_id, "assignee_id": activity.user_id.id,
                     "due_date": str(activity.date_deadline), "summary": activity.summary}
        return {"operation_id": ledger.operation_id, "payload_hash": ledger.payload_hash, "record": value}

    @api.model
    def status(self, operation_id):
        b = self._binding()
        try:
            UUID(operation_id)
        except (ValueError, TypeError):
            invalid("invalid_input")
        ledger = self._model("ops.operation", b).search([("operation_id", "=", operation_id), ("company_id", "=", b.company_id.id)], limit=1)
        return self._receipt(ledger, b) if ledger else None

    @api.model
    def execute(self, envelope, signature):
        self._binding()
        key = os.environ.get('OPS_SIGNING_KEY', '')
        if (len(key) < 32 or not isinstance(envelope, dict) or not isinstance(signature, str)
                or not hmac.compare_digest(signature, hmac.new(key.encode(), canonical(envelope).encode(), hashlib.sha256).hexdigest())):
            raise AccessError('OPS:invalid_signature')
        # Use a fresh READ COMMITTED transaction: the JSON-2 authentication transaction
        # already has a repeatable-read snapshot and cannot safely refresh after locks.
        # Only this transaction writes business data; its ledger commits with the effect.
        with self.env.registry.cursor() as cursor:
            cursor.execute('SET TRANSACTION ISOLATION LEVEL READ COMMITTED')
            scoped = self.with_env(api.Environment(cursor, self.env.uid, {}))
            result = scoped._execute_atomic(envelope, signature)
            cursor.commit()
            return result

    def _execute_atomic(self, envelope, signature):
        self.env.cr.execute("SET LOCAL lock_timeout = '3s'")
        self.env.cr.execute("LOCK TABLE ops_connection, res_company, res_currency, res_partner, product_template, product_product, product_pricelist, product_pricelist_item, uom_uom, crm_lead, res_users, res_company_users_rel, product_taxes_rel IN SHARE ROW EXCLUSIVE MODE")
        b = self._binding()
        key = os.environ.get("OPS_SIGNING_KEY", "")
        if len(key) < 32 or not isinstance(signature, str) or not isinstance(envelope, dict):
            raise AccessError("OPS:invalid_signature")
        expected = hmac.new(key.encode(), canonical(envelope).encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise AccessError("OPS:invalid_signature")
        if envelope.get("tenant") != b.tenant or envelope.get("company_id") != b.company_id.id or envelope.get("contract_version") != "1.0":
            raise AccessError("OPS:scope_mismatch")
        if envelope.get("actor_id") == envelope.get("approver_id"):
            raise AccessError("OPS:self_approval")
        UUID(envelope["operation_id"])
        previous = self._model("ops.operation", b).search([("operation_id", "=", envelope["operation_id"])], limit=1)
        if previous:
            if previous.company_id != b.company_id or previous.payload_hash != envelope["payload_hash"]:
                invalid("idempotency_conflict")
            return self._receipt(previous, b)
        if time.time() >= envelope["expires_at"]:
            invalid("approval_expired")
        preview = self._preview(envelope["kind"], envelope["payload"], b)
        if fingerprint(preview) != envelope["payload_hash"]:
            invalid("stale_proposal")
        if envelope["kind"] == "quote":
            order = self._model("sale.order", b).create({"partner_id": preview["customer_id"],
                "company_id": b.company_id.id, "pricelist_id": preview["pricelist_id"],
                "client_order_ref": "ops:" + envelope["operation_id"],
                "order_line": [(0, 0, {"product_id": line["product_id"], "product_uom_qty": line["quantity"],
                                      "price_unit": float(line["unit_price"]), "discount": 0,
                                      "tax_ids": [(5, 0, 0)]}) for line in preview["items"]]})
            external_id = order.id
            if (order.state != 'draft' or order.partner_id.id != preview['customer_id']
                    or order.company_id != b.company_id or order.currency_id.name != preview['currency']
                    or Decimal(str(order.amount_total)) != Decimal(preview['total'])
                    or len(order.order_line) != len(preview['items'])):
                invalid('postcondition_failed')
            expected = sorted(preview['items'], key=lambda line: line['product_id'])
            actual = order.order_line.sorted(lambda line: line.product_id.id)
            for line, approved in zip(actual, expected):
                if (line.product_id.id != approved['product_id'] or line.product_uom_qty != approved['quantity']
                        or Decimal(str(line.price_unit)) != Decimal(approved['unit_price'])
                        or line.discount or line.tax_ids):
                    invalid('postcondition_failed')
        else:
            activity = self._model("mail.activity", b).create({
                "res_model_id": self.env["ir.model"]._get_id("crm.lead"), "res_id": preview["opportunity_id"],
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                "user_id": preview["assignee_id"], "date_deadline": preview["due_date"], "summary": preview["summary"]})
            external_id = activity.id
        ledger = self._model("ops.operation", b).create({"operation_id": envelope["operation_id"],
            "company_id": b.company_id.id, "kind": envelope["kind"], "external_id": external_id,
            "payload_hash": envelope["payload_hash"]})
        return self._receipt(ledger, b)
