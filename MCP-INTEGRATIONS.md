# Custom MCP Server, APIs & Database

Proyek 02: **Odoo Business Operations MCP Server**

Tanggal rencana: 2026-10-08. Status: **Phase 0–2 selesai; alur deterministik Odoo lokal terimplementasi dan diuji. Phase 3–4 implementasi offline selesai; Phase 5–10 belum selesai**. Checklist hanya dicentang setelah artefak dan verifikasinya tersedia.

## Arsitektur keputusan

Assistant/client → **custom MCP server TypeScript** → domain API **Python** → **PostgreSQL** dan adapter **Odoo**. MCP server tidak melewati business validation dengan menulis tabel langsung. AI memperoleh data SQL melalui query service yang terotorisasi dan terparameterisasi.

MCP server proyek ini punya capability spesifik, bukan server generik yang mengekspos semua API. Jika memakai konektor 02/03, import atau panggil kontraknya; jangan menyalin codebase konektor.

## Tools rencana

| Tool | Jenis | Kontrak ringkas |
| --- | --- | --- |
| `odoo.customer_search` | read | query + authenticated scope → record terbatas |
| `odoo.opportunity_get` | read | opportunity ID → konteks |
| `odoo.quote_prepare` | prepare | items + customer → validated proposal |
| `odoo.activity_prepare` | prepare | opportunity + due date → proposal |
| `odoo.execute_approved` | write | proposal + approval + idempotency → external reference |
| `odoo.operation_status` | read | operation ID → read-back outcome |

## Syarat kontrak

- [x] Pin MCP SDK dan protocol version yang didukung client; gunakan stdio untuk client lokal bila sesuai, authenticated HTTP untuk remote hanya saat deployment terakhir.
- [x] Setiap tool memiliki description, strict input/output schema, source references, stable error codes, pagination bila perlu, dan output limits.
- [x] Server memverifikasi identity, tenant/record scope, role, approval payload/version, serta idempotency key; input model bukan otorisasi.
- [x] Write tools membutuhkan proposal dan approval sesuai risiko. Approval tidak boleh dibuat oleh agent yang hendak melakukan action tersebut.
- [x] Uji protocol dari client, schema rejection, credentials expiry, injection, cancellation, error propagation, concurrency, dan retry.
- [x] Simpan correlation ID dari assistant → MCP → Python → platform; logs cukup untuk diagnosis tanpa body sensitif secara default.

## Model data awal

tenant, actor, platform_connection, tool_contract_version, operation, proposal, approval, external_record_map, idempotency_record, audit_event.

Tambahkan tenant foreign keys, unique constraints untuk external references/idempotency, optimistic versioning atau locking sesuai transaksi, migrations, retention, dan audit. SQL read-only query untuk reporting tidak menerima arbitrary SQL dari model.

**Selesai ketika:** satu alur melalui MCP mengubah atau membaca platform sesuai scope, database mencatat provenance, dan hasil benar dibuktikan lewat read-back/expected state. Unit tests langsung ke fungsi belum cukup untuk protocol acceptance.

## Hubungan dengan automation engine

MCP server custom tetap bisa dipanggil client tanpa n8n. n8n consumer hanya contoh opsional; server tidak menggantungkan startup/health pada engine tersebut.

Evidence implementasi: [Phase 4](docs/PHASE-4.md). Scope saat ini protokol nyata dengan downstream simulasi; connected acceptance dan cloud transport tetap gate berikutnya.
