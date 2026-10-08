# Odoo Business Operations MCP Server

Proyek 02: **Odoo Business Operations MCP Server**

Tanggal rencana: 2026-10-08. Status: **Phase 0-9 selesai untuk scope lokal terpilih; deployment cloud Phase 10 belum selesai**. Claude/Grok opsional dan belum live-validated. Evaluasi Phase 7 adalah regresi sintetis; bukan klaim generalisasi atau ROI manusia.

**Pengguna:** Sales operations dan administrator Odoo.

**Hasil bisnis:** Memberi assistant akses yang terbatas dan dapat diaudit untuk membaca data Odoo serta menyiapkan perubahan bisnis tanpa akses database bebas.

**Alur:** Permintaan operator → assistant memilih skill → tools membaca Odoo → proposal perubahan → preview → approval → eksekusi → read-back Odoo → receipt dan audit.

**Stack keputusan:** TypeScript custom MCP server; Python + FastAPI untuk workflow, validasi, dan automation; assistant client TypeScript; PostgreSQL; Odoo API sesuai versi yang dipilih; Docker Compose di Linux; OpenAI, Claude, Grok; Ollama.

**Automation:** Custom MCP server mandiri; n8n bukan dependency atau release gate. Lihat [N8N-AUTOMATION.md](N8N-AUTOMATION.md).

Pilihan framework adalah keputusan implementasi kita, bukan klaim bahwa JD mewajibkan merek framework tersebut. Versi API/library/model ditetapkan saat Phase 0 berdasarkan dokumentasi resmi dan lingkungan yang tersedia.

## Baseline dan reuse

Proyek baru. Menjadi konektor bersama untuk proyek 04, 05, dan 08. Tetap punya assistant reference, workflow Python, dan bukti uji sendiri; hasilnya bukan hanya daftar endpoint MCP.

## Dokumen kerja

- [Jalur pembelajaran dan tag per phase](docs/LEARNING-PATH.md)
- [PHASES.md](PHASES.md)
- [AI-AGENTS.md](AI-AGENTS.md)
- [REUSABLE-SKILLS.md](REUSABLE-SKILLS.md)
- [MCP-INTEGRATIONS.md](MCP-INTEGRATIONS.md)
- [BUSINESS-PLATFORM.md](BUSINESS-PLATFORM.md)
- [LOCAL-AI-AND-PROVIDERS.md](LOCAL-AI-AND-PROVIDERS.md)
- [SECURITY-TESTING-MONITORING.md](SECURITY-TESTING-MONITORING.md)
- [PROJECT-DELIVERY.md](PROJECT-DELIVERY.md)

## Ukuran keberhasilan

tool task success; correct record selection; unauthorized-write rejection; duplicate effects; proposal correctness; p95 tool execution; verified operations per minute; biaya per tugas benar.

## Cara mulai

1. Ikuti [local setup](docs/LOCAL-SETUP.md) untuk menjalankan fondasi; ikuti [panduan Odoo](docs/ODOO-LOCAL.md) untuk alur bisnis; pekerjaan berikutnya adalah Phase 8 pada PHASES.md.
2. Catat apa yang existing, perlu verifikasi, dan baru. Semua checklist folder ini dimulai belum selesai.
3. Buat satu alur lengkap, uji hasilnya, baru tambah variasi; ikuti urutan fase dan dependency.
4. Catat evidence path/run ID saat menutup fase. Cloud hanya pada Phase 10.

Fondasi aplikasi lokal tersedia di backend/ dan client/, dengan PostgreSQL migrations, Docker Compose, serta automated tests. Assistant dan business skills selesai untuk scope offline Phase 3; custom MCP server tersedia pada Phase 4. Lihat [local setup](docs/LOCAL-SETUP.md).

## Progress implementasi

Phase 0 selesai pada 2026-10-08 untuk inventaris dan scope. Lihat [Phase 0](docs/PHASE-0.md), [acceptance cases](docs/ACCEPTANCE-CASES.md), dan [dependencies](docs/DEPENDENCIES.md). Phase 1 selesai; lihat [hasil dan evidence](docs/PHASE-1.md). Alur pertama: customer search → quotation preview → approval → create draft → read-back. Target sandbox: Odoo Community 19.0 lokal; JSON-2 dan alur quotation/activity telah diuji pada Phase 2. Docker engine telah dipulihkan dan digunakan untuk verifikasi Phase 1.

Phase 2 selesai: customer/opportunity reads, quotation/activity proposal, approval, execute dan read-back terverifikasi. Lihat [hasil Phase 2](docs/PHASE-2.md). API lokal: http://127.0.0.1:8020/docs; Odoo sandbox: http://127.0.0.1:8069.

Phase 3 implementasi offline selesai: assistant, empat reusable skills, adapter provider,
client TypeScript dan durable task journal; 49 tes Python + 2 tes client lulus.
Pengujian AI nyata/Odoo baru menjadi gate Phase 6. Lihat [Phase 3](docs/PHASE-3.md).

Phase 4 implementasi MCP offline selesai: 10 tools, protokol stdio nyata, dan 7 scenario tests. Lihat [Phase 4](docs/PHASE-4.md).

Phase 5 implementasi worker offline selesai: antrean SQLite persisten, dedup event, scheduler, lease dan recovery; 16 tes worker serta 8 tes MCP lulus. Lihat [Phase 5](docs/PHASE-5.md). Jalankan seluruh pemeriksaan ringan dengan `.venv/Scripts/python.exe deploy/check_offline.py`. Docker dan inference nyata belum dijalankan untuk Phase 3–5.

Phase 6 selesai untuk scope lokal terpilih: integrasi Docker/Odoo lulus 38 tes regresi dan 7 skenario assistant/MCP/worker terhubung dan 5 canary AI lokal nyata (Ollama CPU). Empat canary OpenAI dan client nyata juga lulus; Claude/Grok opsional dan belum live-validated. Lihat [status dan reproduksi Phase 6](docs/PHASE-6.md).

Phase 7 selesai: profil OpenAI `gpt-4.1-mini-2025-04-14` / `intent-v4-openai` lulus **18/18** kasus regresi sintetis melalui assistant/MCP/Odoo. Qwen2.5 0.5B lokal mendapat **7/18** dan tetap eksperimental. Tersedia guard jumlah barang, dataset/rubric beku, serta laporan hasil dan batas klaim pada [Phase 7](docs/PHASE-7.md).

Phase 8 selesai: 124 tugas load lokal, 31 draft quotation terverifikasi tanpa duplikasi, serta backup/restore, database recovery dan rollback image teruji. Metrik per tenant, tracing durasi Odoo, dan alert dengan receiver lokal tersedia. Lihat [hasil reliability](docs/PHASE-8.md) dan [runbook operator](docs/LOCAL-RUNBOOK.md). Phase 9 melengkapi delivery pack; cloud tetap Phase 10.

Phase 9 selesai: [delivery pack](PROJECT-DELIVERY.md), [panduan operator](docs/USER-GUIDE.md), [demo CLI nyata](docs/demo/index.html), dan [rancangan Azure beserta estimasi](docs/AZURE-PLAN.md). Aplikasi tetap pada source Phase 8 yang sudah diuji. Cloud belum diprovision.
