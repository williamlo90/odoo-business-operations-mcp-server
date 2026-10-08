# Jalur pembelajaran per phase

Setiap tag menyimpan versi tetap untuk bahan modul. Branch `learning-phases` memuat rangkaian baru: satu commit untuk setiap Phase 3–5. Branch `main` mempertahankan riwayat sebelum rangkaian ini.

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
`git switch learning-phases` untuk kembali ke versi terbaru. Untuk mengerjakan latihan:

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

Untuk phase berikutnya, selesaikan implementasi dan verifikasi gate phase,
lalu buat tepat satu commit dan annotated tag pada commit penyelesaiannya. Tag yang sudah
digunakan sebagai bahan modul tetap; koreksi berikutnya memakai tag versi baru.

Roadmap revisi memakai Phase 0–10. Phase 3–5 merupakan checkpoint implementasi offline; validasi terhubung dikumpulkan pada Phase 6. Gunakan tag `phase-3-code` untuk checkpoint assistant.

Tag `phase-4-code` menyimpan server MCP dan integrasi assistant melalui protokol stdio.

| Checkpoint offline | Satu commit pembelajaran | Panduan |
| --- | --- | --- |
| `phase-3-code` | Assistant, providers, shared skills, durable task journal | `docs/PHASE-3.md` |
| `phase-4-code` | MCP server, scoped tools, reference transport | `docs/PHASE-4.md` |
| `phase-5-code` | Worker, persistent queue, scheduling and recovery | `docs/PHASE-5.md` |

Gunakan `git show phase-4-code` untuk mempelajari perubahan satu phase,
atau `git diff phase-3-code phase-4-code` untuk membandingkan checkpoint.
`git switch --detach phase-5-code` membuka checkpoint terakhir sebelum Docker.
Jalankan `python deploy/check_offline.py` dari virtual environment yang sudah
memiliki dependencies. Runner membangun TypeScript dan menjalankan tes ringan
secara berurutan tanpa Docker, provider nyata atau model lokal.

## Connected and quality checkpoints

| Tag | One phase, one commit | Guide |
| --- | --- | --- |
| `phase-6-integration` | Docker/Odoo, MCP/worker, OpenAI and local inference validation; Claude/Grok optional | `docs/PHASE-6.md` |
| `phase-7-quality` | Frozen evaluation, quantity grounding, versioned intent prompt and quality evidence | `docs/PHASE-7.md` |

Compare these stages with `git diff phase-6-integration phase-7-quality`.
Phase 7 qualification is a synthetic regression result. The local 0.5B model
remains experimental; the tested OpenAI profile is the qualified option.

| Reliability checkpoint | One phase, one commit | Guide |
| --- | --- | --- |
| `phase-8-reliability` | Scoped metrics, numeric guard hardening, bounded load, recovery/alerts/rollback evidence | `docs/PHASE-8.md` |

Use `git diff phase-7-quality phase-8-reliability` to study this phase. Phase 7's frozen evaluation remains reproducible at its own tag; Phase 8 uses assistant
contract `0.3.2` and its separately recorded control/canary evidence.

Phase 9 memakai satu commit/tag `phase-9-delivery`: panduan penggunaan, recorded CLI demo, verifikasi manifest, handover dan rencana Azure. Gunakan `git diff phase-8-reliability phase-9-delivery` untuk mempelajari delivery tanpa perubahan perilaku aplikasi.
