# Odoo Business Operations MCP Server

Proyek 02: **Odoo Business Operations MCP Server**

Tanggal rencana: 2026-10-08. Status: **Phase 0–1 selesai; fondasi lokal terimplementasi dan diuji. Phase 2–9 belum selesai**. Checklist hanya dicentang setelah artefak dan verifikasinya tersedia.

**Pengguna:** Sales operations dan administrator Odoo.

**Hasil bisnis:** Memberi assistant akses yang terbatas dan dapat diaudit untuk membaca data Odoo serta menyiapkan perubahan bisnis tanpa akses database bebas.

**Alur:** Permintaan operator → assistant memilih skill → tools membaca Odoo → proposal perubahan → preview → approval → eksekusi → read-back Odoo → receipt dan audit.

**Stack keputusan:** TypeScript custom MCP server; Python + FastAPI untuk workflow, validasi, dan automation; assistant client TypeScript; PostgreSQL; Odoo API sesuai versi yang dipilih; Docker Compose di Linux; OpenAI, Claude, Grok; Ollama.

**Automation:** Custom MCP server mandiri; n8n bukan dependency atau release gate. Lihat [N8N-AUTOMATION.md](N8N-AUTOMATION.md).

Pilihan framework adalah keputusan implementasi kita, bukan klaim bahwa JD mewajibkan merek framework tersebut. Versi API/library/model ditetapkan saat Phase 0 berdasarkan dokumentasi resmi dan lingkungan yang tersedia.

## Baseline dan reuse

Proyek baru. Menjadi konektor bersama untuk proyek 04, 05, dan 08. Tetap punya assistant reference, workflow Python, dan bukti uji sendiri; hasilnya bukan hanya daftar endpoint MCP.

## Dokumen kerja

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

1. Ikuti [local setup](docs/LOCAL-SETUP.md) untuk menjalankan fondasi; pekerjaan berikutnya adalah Phase 2 pada PHASES.md.
2. Catat apa yang existing, perlu verifikasi, dan baru. Semua checklist folder ini dimulai belum selesai.
3. Buat satu alur lengkap, uji hasilnya, baru tambah variasi; ikuti urutan fase dan dependency.
4. Catat evidence path/run ID saat menutup fase. Cloud hanya pada Phase 9.

Fondasi aplikasi lokal tersedia di backend/ dan client/, dengan PostgreSQL migrations, Docker Compose, serta automated tests. MCP server dan business skills executable menunggu Phase 3–4. Lihat [local setup](docs/LOCAL-SETUP.md).

## Progress implementasi

Phase 0 selesai pada 2026-10-08 untuk inventaris dan scope. Lihat [Phase 0](docs/PHASE-0.md), [acceptance cases](docs/ACCEPTANCE-CASES.md), dan [dependencies](docs/DEPENDENCIES.md). Phase 1 selesai; lihat [hasil dan evidence](docs/PHASE-1.md). Alur pertama: customer search → quotation preview → approval → create draft → read-back. Target sandbox: Odoo Community 19.0 lokal; akses dan compatibility belum diuji. Docker engine telah dipulihkan dan digunakan untuk verifikasi Phase 1.
