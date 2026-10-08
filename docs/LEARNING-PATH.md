# Jalur pembelajaran per phase

Setiap tag menyimpan versi tetap untuk bahan modul. Branch `main` berisi perkembangan terbaru.

| Tag | Fokus | Materi dan hasil |
| --- | --- | --- |
| `phase-0` | Scope dan perencanaan | Batas V1, inventaris, dependency, 20 acceptance cases sebelum implementasi |
| `phase-1` | Fondasi aplikasi lokal | FastAPI, PostgreSQL, autentikasi, role, isolasi tenant, Docker dan client TypeScript; 17 tes lulus |
| `phase-2` | Integrasi bisnis Odoo | Proposal, approval, draft quotation/activity, idempotency dan read-back; 38 tes lulus |

## Membuka materi

```bash
git clone https://github.com/williamlo90/odoo-business-operations-mcp-server.git
cd odoo-business-operations-mcp-server
git switch --detach phase-0
```

Ganti tag dengan `phase-1` atau `phase-2` untuk tahap berikutnya. Gunakan
`git switch main` untuk kembali ke versi terbaru. Untuk mengerjakan latihan:

```bash
git switch -c latihan-phase-1 phase-1
```

Pada Phase 1, ikuti `docs/LOCAL-SETUP.md`. Pada Phase 2, lanjutkan dengan
`docs/ODOO-LOCAL.md`. Gunakan database/volume terpisah saat menjalankan versi lama;
checkout Git hanya mengganti source, bukan menurunkan versi schema database.
Kredensial lokal dibuat melalui panduan setup dan tidak disertakan dalam repository.

## Susunan modul

Setiap modul dapat mengikuti urutan: tujuan belajar, prasyarat, pembahasan alur,
praktik dari tag terkait, verifikasi hasil, lalu latihan mandiri. Materi di sini
menjadi peta modul; belum merupakan modul pembelajaran lengkap.

Tag Phase 0 merupakan snapshot perencanaan yang disusun dari artefak tersimpan,
dengan commit tersendiri. Tag Phase 1 dan 2 menunjuk commit implementasi yang
sudah diverifikasi. Riwayat commit implementasi tetap dipertahankan.

Untuk phase berikutnya, buat commit selama pengerjaan, verifikasi gate phase,
lalu buat annotated tag `phase-N` pada commit penyelesaiannya. Tag yang sudah
digunakan sebagai bahan modul tetap; koreksi berikutnya memakai tag versi baru.
