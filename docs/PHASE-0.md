# Phase 0 — Scope dan keputusan implementasi

Tanggal: 2026-10-08 (Asia/Jakarta). Run: `phase0-20261008-01`.
Status: inventaris dan scope selesai; implementasi dan connected validation belum dilakukan.

## Tujuan dan ownership

Membantu sales operations menyiapkan transaksi Odoo yang benar, dengan preview,
approval manusia, dan verifikasi hasil. William menjadi owner proyek/demo lokal
berdasarkan README portfolio. Belum ada business owner pelanggan eksternal.
William mengelola konfigurasi dan akses sandbox; role operator dan approver memakai
akun uji terpisah meskipun demo dijalankan oleh satu orang.

Alur pertama yang disetujui pengguna: cari pelanggan → proposal quotation →
preview → approval → buat satu draft quotation → read-back dan receipt.

## Tiga perjalanan pengguna V1

| Journey | Hasil benar | Batas |
| --- | --- | --- |
| J1: riset pelanggan | Record ID, company, dan profil dari sumber Odoo; pelanggan ambigu meminta pilihan eksplisit | Read-only, company scope dari server |
| J2: tinjau opportunity dan siapkan follow-up | Konteks opportunity bersumber; activity dengan penanggung jawab, tanggal, dan target benar | Membuat activity hanya setelah approval; sesudah alur quotation selesai |
| J3: siapkan quotation | Proposal dengan customer, company, currency, items, harga, total, lalu tepat satu draft Odoo setelah approval | Tidak mengonfirmasi sales order atau mengirim quotation |

Scope release tetap mencakup keempat skills pada REUSABLE-SKILLS.md. J3 merupakan
alur pertama, bukan pengganti J1/J2 atau penghapusan gate fase berikutnya.

## Batas V1 dan aturan bisnis

- Data sintetis dan sandbox lokal. Company A dan B memakai isolasi eksplisit;
  record pelanggan bersama lintas company tidak dipakai pada fixture awal.
- Operator membaca dan membuat proposal; approver terpisah menyetujui dalam scope;
  administrator mengelola konfigurasi tanpa otomatis memperoleh hak approval.
- Harga dihitung deterministik dari katalog/pricelist dan policy, bukan dari LLM.
  Fixture pertama memakai IDR, tanpa diskon/pajak, qty positif dan produk aktif.
  Konfigurasi pajak/diskon/pricing yang belum didukung ditolak secara eksplisit.
- Odoo adalah sumber record bisnis, katalog dan final quotation. Database aplikasi
  menyimpan proposal, approval, operation, idempotency dan audit; tidak menulis
  langsung ke database Odoo.
- Approval mengikat actor, tenant/company, payload hash, versi sumber, expiry dan
  policy. Perubahan customer, item, pricing atau record relevan membutuhkan preview
  serta approval baru. Pengecekan perubahan harus menutup race saat write; desain
  transaksi/addon Odoo diputuskan dan diuji di Phase 2 sebelum mengklaim jaminan ini.
- Duplicate/concurrent request harus menghasilkan satu efek. Timeout setelah write
  menjadi `unknown` sampai rekonsiliasi. Tidak melakukan create ulang secara buta.
- Di luar V1: konfirmasi order, invoice, payment, stock movement, delete record,
  outbound email, arbitrary SQL/model method/URL, dan deployment cloud sebelum Phase 9.

## Keputusan teknis

| Area | Keputusan |
| --- | --- |
| Platform | Target Odoo Community 19.0 lokal dengan Contacts, CRM, Sales; JSON-2 menjadi API target. Model/method dan akses nyata wajib diverifikasi sebelum adapter di Phase 2 |
| Runtime | Linux containers melalui Docker Compose; Windows/WSL2 sebagai development host |
| Services | Python + FastAPI domain service, TypeScript MCP server dan reference client, PostgreSQL |
| Versions | Odoo line 19.0 dipilih; patch/image digest, Python/container, PostgreSQL, SDK/protocol dan dependency lock ditetapkan melalui compatibility smoke pada Phase 1; belum ada executable untuk dipin |
| MCP | Stdio untuk reference client lokal; HTTP remote menunggu Phase 9 |
| Automation | Worker/scheduler Python memakai service/skills yang sama; n8n not selected |
| AI | Satu orchestrator; OpenAI/Claude/Grok adapters serta Ollama sesuai Phase 3. Default model ditentukan setelah uji; model/license/revision belum dipilih |
| Resource | Mulai concurrency inference 1; pemilihan model lokal mengikuti RAM/VRAM terukur, belum merupakan klaim model fit/performance |

Dokumentasi resmi menjelaskan JSON-2 pada Odoo 19 dan keamanan mengikuti Odoo.
Akses API hosted memiliki batas plan; pilihan lokal ini tidak mengklaim akses
gratis ke Odoo Online. Endpoint aktual tetap dependency verifikasi.

Sumber: [JSON-2 API](https://www.odoo.com/documentation/19.0/developer/reference/external_api.html),
[source install](https://www.odoo.com/documentation/19.0/administration/on_premise/source.html),
[lisensi source Community](https://github.com/odoo/odoo/blob/19.0/LICENSE).
Lisensi source Odoo adalah LGPLv3; image/dependency notices dicatat saat provisioning.

## Inventaris dan strategi reuse

| Kemampuan | Kategori | Keputusan |
| --- | --- | --- |
| Sepuluh dokumen rencana | existing / reuse | Pertahankan sebagai kontrak; hash awal ada pada evidence manifest |
| Runtime Git/Python/Node/Docker/WSL | existing / needs-verification | CLI ditemukan; Docker engine belum terhubung |
| Odoo sandbox, modul, API account | new / needs-verification | Provision sandbox terisolasi; tidak mengasumsikan instance lama bisa dipakai |
| Backend, client, MCP, DB migrations | new | Dibangun Phase 1–4; belum ada source executable di folder |
| Skills, worker, evaluasi, monitoring | new | Mengikuti fase dan acceptance proyek |
| Kode proyek lain | not selected | Tidak mengimpor atau mengubah working tree proyek lain |
| Kontrak consumer 04/05/08 | new | Proyek 02 menjadi producer; consumer bukan blocker pembangunan 02 |

Strategi: retain planning pack, bangun implementasi baru, tanpa replace/delete/import
source. Tidak ada source revision atau dirty Git diff karena folder belum merupakan
repository. Tidak ada klaim audit source di luar folder ini.

## Gate dan handoff

Artefak gate: inventaris di dokumen ini, scope V1/J1–J3, [acceptance cases](ACCEPTANCE-CASES.md),
[dependency register](DEPENDENCIES.md), [baseline](evidence/phase0-baseline.json),
dan [hasil pemeriksaan](evidence/phase0-environment.md).

Phase 0 selesai sebagai inventaris, dengan dependency terbuka yang tercatat.
Phase 1 dimulai dengan mengaktifkan Docker engine, membuat Git repository lokal,
menetapkan runtime/dependency lock, lalu membangun auth dan satu alur lokal dengan
PostgreSQL, seed sintetis, serta smoke test. Provider keys tidak memblokir fondasi
deterministik. Tidak ada test aplikasi yang dinyatakan lulus pada Phase 0.
