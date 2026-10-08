# Reusable Business Skills

Proyek 02: **Odoo Business Operations MCP Server**

Tanggal rencana: 2026-10-08. Status: **Phase 0–2 selesai; alur deterministik Odoo lokal terimplementasi dan diuji. Phase 3–4 implementasi offline selesai; Phase 5–10 belum selesai**. Checklist hanya dicentang setelah artefak dan verifikasinya tersedia.

Skills di sini adalah paket kemampuan aplikasi yang dipakai assistant dan automation worker. Saat implementasi, setiap skill memiliki `skills/<name>/SKILL.md` beserta schema, implementation binding (Python handler atau n8n sub-workflow sesuai keputusan), dan tests; ini bukan sekadar kumpulan prompt atau asumsi bahwa sebuah Codex skill sudah terpasang.

| Skill | Input | Output | Batas tindakan |
| --- | --- | --- | --- |
| `research_customer` | customer reference | profil dengan sumber record | read-only |
| `prepare_quote` | kebutuhan + catalog + pricing rules | draft quotation tervalidasi | harga dihitung deterministik |
| `prepare_crm_activity` | opportunity + follow-up intent | preview activity | approval untuk write |
| `reconcile_odoo_write` | operation ID | confirmed/unknown/failed | lookup sebelum retry |

## Isi wajib setiap paket skill

- [ ] SKILL.md: masalah bisnis, kapan dipakai/tidak dipakai, owner, preconditions, urutan langkah, exception handling, dan contoh.
- [ ] Input/output JSON Schema berversi serta implementation binding Python atau n8n sub-workflow; aturan transaksi/izin tetap di service otoritatif dan tidak diduplikasi dalam prompt.
- [ ] Declared tools dan permissions minimum; approval requirement dan side-effect classification.
- [ ] Timeout, retries, idempotency, cancellation, postcondition check, dan compensation/manual recovery bila relevan.
- [ ] Fixtures dengan normal/ambiguous/failure cases; expected results ditulis terpisah dari generation.
- [ ] Changelog/compatibility metadata dan metrik task correctness, latency, cost, serta error classification.

## Bukti reusable

- Skill yang sama dipanggil dari assistant interaktif dan automation worker tanpa menyalin core logic.
- Business/tenant configuration kedua menggunakan skill yang sama dengan policy/config berbeda.
- Menukar hosted model ke local model tidak mengubah aturan izin atau syarat approval.
- Skill gagal dengan status yang jelas jika data atau izin kurang; worker retry tidak menggandakan side effect.

**Selesai ketika:** semua skill tabel punya implementasi executable, kontrak, dokumentasi, dan tes; satu penggunaan ulang lintas caller dibuktikan dalam evidence.
