# Dependency register

Tanggal pemeriksaan: 2026-10-08. Owner semua tindakan lokal: William/proyek 02.
`blocked` di tabel berarti gate terkait belum dapat diverifikasi, bukan seluruh
proyek berhenti. Tidak ada nilai secret disimpan dalam dokumen.

| ID | Dependency / status | Gate terdampak | Penyelesaian dan bukti yang dibutuhkan |
| --- | --- | --- | --- |
| D01 | Resolved Phase 1: Docker Engine 29.8.0 berjalan | Phase 1 local smoke | Aktifkan Docker Desktop Linux engine, cek server version dan isolated Compose smoke |
| D02 | Resolved Phase 1: Linux containers berjalan melalui Docker Desktop/WSL2 | Phase 1 | Validasi Linux container startup; tidak mengubah distro/proyek lama |
| D03 | Resolved Phase 2: Odoo Community 19.0-20260926 lokal dengan JSON-2 dan addon ops_bridge | Phase 2 adapter / Phase 6 connected | Buat DB sandbox dan akun scoped, install modul, cek JSON-2 dan field/model pada instance; simpan read/write/read-back evidence |
| D04 | Resolved Phase 2: scoped keys pada private local/odoo-config/connections.json, mount read-only ke API | Connected tests | Buat dedicated local service account; secret di env lokal terabaikan Git; akses hosted tidak dipilih |
| D05 | Resolved Phase 1: Git repository lokal main tersedia | Phase 1 | Init repo khusus folder 02, ignore secrets/generated artifacts, snapshot awal |
| D06 | Phase 1 validated: container Python 3.13.16, Node 22.23.3; dependency lock dan image digest tersedia; MCP SDK 2.3.1 / protocol 2026-07-28 diuji offline Phase 4 | Phase 1 | Pilih runtime containers dan pin package/image versions setelah smoke; catat versi MCP protocol/SDK |
| D07 | Aplikasi: PostgreSQL 17.11 tervalidasi Phase 1. Database Odoo terpisah tervalidasi Phase 2 | Phase 1/2 | Pisahkan database dan akun; migrations, seed/reset hanya DB uji proyek ini |
| D08 | OpenAI terkonfigurasi lokal dan live canary lulus; Anthropic/xAI opsional, belum live-validated | Phase 6 real canary | Owner menyediakan env melalui mekanisme secret; contract tests dapat berjalan sebelumnya; tidak menganggap keys tidak ada di seluruh mesin |
| D09 | Resolved local Phase 6: Ollama 0.40.1 portable CPU, Qwen2.5 0.5B Q4_K_M Apache-2.0; digest dipin | Phase 6 inference | Install/runtime check, pilih model sesuai resource, catat license/revision/quantization dan jalankan inference nyata |
| D10 | Company A/B dan customers sintetis tersedia Phase 1; pricing dan mapping Odoo A/B tervalidasi Phase 2 | Phase 2/5 | Seed sintetis dan verifikasi isolasi company serta expected totals |
| D11 | Consumer 04/05/08 belum terintegrasi | Compatibility/reuse | Publikasikan kontrak berversi dan fixtures pada Phase 2; bukan dependency masuk untuk 02 |
| D12 | Resolved Phase 2 lokal: signed envelope, fresh READ COMMITTED transaction, source locks dan unique operation ledger | Phase 2/5 write acceptance | Pilih addon/transaction boundary yang menegakkan source version dan unique operation ID; buktikan race/timeout/concurrency; app lock saja tidak membuktikan atomic Odoo write |

Tidak perlu kredensial cloud Azure untuk Phase 0–9. n8n not selected, bukan blocked.

Update Phase 1: lihat [delivery dan evidence](PHASE-1.md). D01/D02/D05 selesai untuk fondasi lokal; D06/D07/D10 tetap memiliki bagian fase berikutnya.

Phase 2: D03/D04/D07/D10/D12 selesai untuk scope sandbox yang diuji. Kontrak D11 tersedia, integrasi consumer tetap pending. Provider/Ollama D08/D09 belum berubah. Lihat [bukti dan limitations](PHASE-2.md).

Phase 5: worker SQLite lokal dan MCP telah diuji offline. Docker, akun automation A/B dan Ollama CPU telah diverifikasi pada Phase 6; OpenAI live canary lulus; Claude/Grok opsional, bukan gate scope terpilih.

Phase 7: profil OpenAI intent-v4-openai lulus gate regresi sintetis 18/18; Qwen2.5 0.5B 7/18 dan tetap eksperimental. Claude/Grok opsional, tidak memblokir scope lokal.
