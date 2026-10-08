# Automation Decision — 02 - Odoo Business Operations MCP Server

Status: **rencana; belum menjadi hasil benchmark atau implementasi baru**.

**Keputusan:** Custom MCP server mandiri; n8n bukan dependency atau release gate.

**Peran:** TypeScript MCP server + Python services + Odoo API. Reference assistant menjalankan tools langsung melalui protocol. Consumer n8n dapat ditambahkan sebagai contoh, bukan kewajiban.

**Alasan:** Konektor dinilai dari kontrak tools, record mapping, authorization, idempotency dan verified writes. Automation lintas aplikasi ditempatkan di 04/08.

Dokumen ini menggantikan kewajiban lama memasang n8n di semua proyek. Lihat [keputusan portfolio](../AUTOMATION-DECISIONS.md).

## Contoh extension, bukan pekerjaan wajib V1

1. **Workflow utama:** Event opportunity berubah atau polling delta Odoo → n8n meminta backend memeriksa kelengkapan → skill yang sama dengan assistant menyiapkan activity proposal → operator melakukan approval → backend menulis dan membaca kembali hasil Odoo.
2. **Monitoring dan tindak lanjut:** Jadwal berkala → backend merekonsiliasi operasi berstatus unknown → n8n menampilkan ringkasan operasi yang membutuhkan perhatian; tidak mengirim ulang create secara buta.

## Ownership dan acceptance

- Pilih pemilik orchestration, retries, approval records dan business state secara eksplisit. Satu operasi bisnis punya satu sumber status otoritatif.
- n8n boleh menjalankan agent, tool calls, branching, wait/approval dan reusable sub-workflows bila cocok. Pembagian Python/n8n adalah keputusan proyek, bukan batas kemampuan n8n.
- Approval dari UI aplikasi maupun workflow harus terikat actor, tenant, payload/version dan kewenangan; penerimaan callback atau teks approved tidak cukup.
- Side effects membutuhkan deduplication/idempotency dan verifikasi hasil. Unknown outcomes direkonsiliasi sebelum retry; state berhasil di engine tidak otomatis berarti masalah bisnis selesai.
- Scope authorization berlaku pada semua jalur: assistant, MCP, worker, automation engine dan direct API.

## Acceptance produk utama

- [ ] Instalasi, workflow utama, protocol/API tests, monitoring, delivery dan deployment lulus tanpa n8n terpasang.
- [ ] Dokumentasikan engine/scheduler yang benar-benar dipilih serta source of truth, retries dan recovery.
- [ ] Tidak ada checklist export workflow atau deployment n8n wajib pada release utama.
- [ ] Jika extension automation dipilih kemudian, catat kebutuhan operator, manfaat, ownership, biaya operasi dan acceptance terpisah sebelum menjadikannya dependency.

Contoh extension di atas tidak boleh mengubah status release utama menjadi belum selesai. n8n yang tidak dipilih dilaporkan not selected, bukan implementation failure.
