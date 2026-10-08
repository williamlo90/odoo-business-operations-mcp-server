# Dependency register

Tanggal pemeriksaan: 2026-10-08. Owner semua tindakan lokal: William/proyek 02.
`blocked` di tabel berarti gate terkait belum dapat diverifikasi, bukan seluruh
proyek berhenti. Tidak ada nilai secret disimpan dalam dokumen.

| ID | Dependency / status | Gate terdampak | Penyelesaian dan bukti yang dibutuhkan |
| --- | --- | --- | --- |
| D01 | Resolved Phase 1: Docker Engine 29.8.0 berjalan | Phase 1 local smoke | Aktifkan Docker Desktop Linux engine, cek server version dan isolated Compose smoke |
| D02 | Resolved Phase 1: Linux containers berjalan melalui Docker Desktop/WSL2 | Phase 1 | Validasi Linux container startup; tidak mengubah distro/proyek lama |
| D03 | Odoo Community 19.0 lokal: planned, belum diprovision | Phase 2 adapter / Phase 5 connected | Buat DB sandbox dan akun scoped, install modul, cek JSON-2 dan field/model pada instance; simpan read/write/read-back evidence |
| D04 | Odoo URL/database/key tidak tersedia pada process env | Connected tests | Buat dedicated local service account; secret di env lokal terabaikan Git; akses hosted tidak dipilih |
| D05 | Resolved Phase 1: Git repository lokal main tersedia | Phase 1 | Init repo khusus folder 02, ignore secrets/generated artifacts, snapshot awal |
| D06 | Phase 1 validated: container Python 3.13.16, Node 22.23.3; dependency lock dan image digest tersedia; MCP SDK/protocol menunggu Phase 4 | Phase 1 | Pilih runtime containers dan pin package/image versions setelah smoke; catat versi MCP protocol/SDK |
| D07 | Aplikasi: PostgreSQL 17.11 tervalidasi Phase 1. Database Odoo masih pending | Phase 1/2 | Pisahkan database dan akun; migrations, seed/reset hanya DB uji proyek ini |
| D08 | OpenAI/Anthropic/xAI keys tidak tersedia pada process env | Phase 3 real canary | Owner menyediakan env melalui mekanisme secret; contract tests dapat berjalan sebelumnya; tidak menganggap keys tidak ada di seluruh mesin |
| D09 | Ollama tidak ditemukan di PATH; model/license belum dipilih | Phase 3 inference | Install/runtime check, pilih model sesuai resource, catat license/revision/quantization dan jalankan inference nyata |
| D10 | Company A/B dan customers sintetis tersedia Phase 1; pricing/Odoo mapping pending Phase 2 | Phase 2/5 | Seed sintetis dan verifikasi isolasi company serta expected totals |
| D11 | Consumer 04/05/08 belum terintegrasi | Compatibility/reuse | Publikasikan kontrak berversi dan fixtures pada Phase 2; bukan dependency masuk untuk 02 |
| D12 | Atomic stale-check dan dedup lintas aplikasi/Odoo: design pending | Phase 2/5 write acceptance | Pilih addon/transaction boundary yang menegakkan source version dan unique operation ID; buktikan race/timeout/concurrency; app lock saja tidak membuktikan atomic Odoo write |

Tidak perlu kredensial cloud Azure untuk Phase 0–8. n8n not selected, bukan blocked.

Update Phase 1: lihat [delivery dan evidence](PHASE-1.md). D01/D02/D05 selesai untuk fondasi lokal; D06/D07/D10 tetap memiliki bagian fase berikutnya.
