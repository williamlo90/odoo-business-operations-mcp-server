# AI Agents, Assistants & Bots

Proyek 02: **Odoo Business Operations MCP Server**

Tanggal rencana: 2026-10-08. Status: **Phase 0–2 selesai; alur deterministik Odoo lokal terimplementasi dan diuji. Phase 3–9 belum selesai**. Checklist hanya dicentang setelah artefak dan verifikasinya tersedia.

## Tugas assistant

Memberi assistant akses yang terbatas dan dapat diaudit untuk membaca data Odoo serta menyiapkan perubahan bisnis tanpa akses database bebas.

Pengguna: Sales operations dan administrator Odoo.

Alur: Permintaan operator → assistant memilih skill → tools membaca Odoo → proposal perubahan → preview → approval → eksekusi → read-back Odoo → receipt dan audit.

## Kemampuan yang dibangun

- Bangun reference assistant untuk mencari pelanggan, meninjau peluang sales, dan menyiapkan draft quotation atau activity.
- Tentukan versi/edition Odoo serta model/API yang benar-benar tersedia; dokumentasikan pilihan sebelum implementasi adapter.
- Pisahkan tool read, prepare, dan execute; tool tidak menyediakan arbitrary SQL, arbitrary model method, atau unrestricted URL.
- Approval terikat payload, actor, tenant, dan versi record. Perubahan payload atau record membatalkan approval lama.
- Tangani pagination, rate limit, timeout, partial failure, retry, dan read-back hasil. Jangan menganggap semua endpoint mendukung idempotency native.
- Sediakan contract versioning dan compatibility fixtures untuk consumer proyek lain.

## Kontrak perilaku

- Input membawa task ID, authenticated actor, tenant, permitted scope, dan referensi data. Scope berasal dari server, bukan dipercaya dari prompt.
- Output minimal: status, facts dengan source references, missing information, proposed actions, reason, dan confidence jika memiliki makna terkalibrasi. Confidence sendiri tidak memberi izin eksekusi.
- Tools dan jumlah langkah dibatasi; ada timeout/cancellation dan terminal state. Tugas di luar kemampuan menghasilkan klarifikasi atau eskalasi.
- Business rules, arithmetic, permissions, approval dan state transitions ditegakkan domain service Python.
- Prompt tidak memuat credentials. Evidence dari dokumen/pesan dianggap input tidak tepercaya, bukan instruksi untuk memperluas akses.
- Bedakan recommendation, approved, dispatched, accepted, verified, failed, dan unknown sesuai kebutuhan proyek. Jangan mengklaim action berhasil hanya dari teks model.
- Mulai satu orchestrator dan skills deterministik. Multi-agent hanya jika pemisahan tanggung jawab memberi manfaat terukur.

## Artefak implementasi yang harus ada

- [ ] Workflow dengan typed contracts, durable state dan recovery path; orchestration mengikuti keputusan proyek (Python atau n8n), bukan wajib dua engine.
- [ ] Assistant UI/reference client TypeScript dengan preview bukti, proposal, approval dan status.
- [ ] Prompt/schema/version registry serta adapters hosted/local.
- [ ] Scenario tests untuk happy path, ambiguous input, refusal/abstention, injection, dan tool failure.
- [ ] Run trace yang menghubungkan input, model/skill/tool versions, approval, hasil tujuan, latency, dan biaya tanpa membocorkan secrets.

**Selesai ketika:** operator dapat menjalankan demo pada PROJECT-DELIVERY.md; hasil diperiksa terhadap reference outcome; kegagalan tidak ditampilkan sebagai sukses.

## Pemilik orchestration

Custom MCP server mandiri; n8n bukan dependency atau release gate. TypeScript MCP server + Python services + Odoo API. Reference assistant menjalankan tools langsung melalui protocol. Consumer n8n dapat ditambahkan sebagai contoh, bukan kewajiban. Konektor dinilai dari kontrak tools, record mapping, authorization, idempotency dan verified writes. Automation lintas aplikasi ditempatkan di 04/08. Lihat [N8N-AUTOMATION.md](N8N-AUTOMATION.md).
