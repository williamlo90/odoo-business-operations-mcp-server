# Dependency pada akhir Phase 0

Ringkasan pembelajaran berdasarkan inventaris Phase 0.

| Dependency | Pekerjaan berikutnya |
| --- | --- |
| Docker engine belum terhubung | Aktifkan dan verifikasi Linux containers pada Phase 1 |
| Belum ada repository/source aplikasi | Bangun fondasi Git, FastAPI, PostgreSQL dan client pada Phase 1 |
| Runtime/dependency container belum dipin | Tetapkan versi dan smoke test pada Phase 1 |
| Odoo sandbox dan kredensial belum tersedia | Provision Community 19, Contacts/CRM/Sales dan akun scoped pada Phase 2 |
| Pricing, stale-check dan dedup Odoo | Tetapkan kontrak serta buktikan transaksi pada Phase 2 |
| Provider keys tidak tersedia pada process env | Konfigurasi dan canary nyata pada Phase 3 |
| Ollama tidak ditemukan di PATH | Verifikasi runtime, model, lisensi dan inference pada Phase 3 |
| Consumer 04/05/08 belum terintegrasi | Siapkan kontrak berversi; bukan blocker fondasi |

Lihat [scope](PHASE-0.md) dan [pemeriksaan lingkungan](evidence/phase0-environment.md).
Cloud menunggu Phase 9. n8n bukan dependency.
