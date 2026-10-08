# Phase Plan & Definition of Done

Proyek 02: **Odoo Business Operations MCP Server**

Tanggal rencana: 2026-10-08. Status: **Phase 0–1 selesai; fondasi lokal terimplementasi dan diuji. Phase 2–9 belum selesai**. Checklist hanya dicentang setelah artefak dan verifikasinya tersedia.

Urutan wajib: **0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9**. Access control dan test dimulai saat feature dibuat; fase 7 merupakan verifikasi menyeluruh, bukan pertama kali security ditambahkan. Tidak ada deployment aplikasi ke cloud sebelum fase 9.

Pemakaian API model atau test tenant SaaS dari aplikasi lokal diperbolehkan pada fase integrasi. Itu berbeda dari deployment aplikasi kita ke cloud. Mode offline proyek 07 tetap tidak memakai API eksternal. Infrastructure-as-code boleh disiapkan sebelum fase 9 tanpa apply/provision.

## Phase 0 — Inventaris dan batas pekerjaan

- [x] Terapkan keputusan automation pada [N8N-AUTOMATION.md](N8N-AUTOMATION.md); n8n bukan dependency atau gate default proyek ini.

- [x] Baca baseline di README; periksa source, Git diff, dan evidence terbaru. Jangan mengubah atau menyalin working tree lama tanpa mencatat perubahan lokal.
- [x] Tentukan owner bisnis, tiga perjalanan pengguna utama, batas tindakan, dan definisi hasil benar.
- [x] Catat akses sandbox, credentials, model hardware/license, versi API, dan dependency proyek lain; dependency yang belum ada diberi status blocked yang spesifik.
- [x] Tentukan strategi retain/replace/delete atau import kode; simpan source revision dan local changes yang diperlukan. Pilihan mengikuti bukti architecture comparison bila berlaku.

**Gate:** daftar kemampuan existing/reuse/new/needs-verification; scope V1; acceptance cases; dependency register. Ini inventaris baru, bukan klaim seluruh baseline telah diaudit ulang.

Evidence Phase 0 (2026-10-08): [scope dan inventaris](docs/PHASE-0.md), [acceptance cases](docs/ACCEPTANCE-CASES.md), [dependency register](docs/DEPENDENCIES.md), [environment checks](docs/evidence/phase0-environment.md), [baseline hashes](docs/evidence/phase0-baseline.json). Gate inventaris selesai; dependency runtime/API/model yang belum terverifikasi tetap terbuka. Tidak ada klaim implementasi atau connected validation.

## Phase 1 — Fondasi aplikasi lokal

- [x] Buat Git repository, backend Python, TypeScript client, PostgreSQL migrations, dan Docker Compose untuk Linux.
- [x] Bangun auth, tenant/role context, konfigurasi tervalidasi, secret melalui environment, health/readiness, structured logs yang disanitasi.
- [x] Sediakan seed data sintetis, local setup dari mesin bersih, reset test database terisolasi, dan automated smoke tests.
- [x] Tetapkan struktur code: backend/, frontend/ atau client/, mcp-server/, skills/, tests/, docs/, deploy/. Ini rencana struktur implementasi; jangan membuat file kode kosong untuk memberi kesan selesai.

**Gate:** user berizin bisa login dan menjalankan satu alur lokal dengan database; user tanpa izin ditolak di server; install guide dapat diikuti ulang.

Evidence Phase 1 (2026-10-08): [delivery dan hasil verifikasi](docs/PHASE-1.md), [panduan instalasi](docs/LOCAL-SETUP.md). 17 tests lulus pada PostgreSQL nyata, demo client lulus, instalasi volume kosong lulus, dan DB outage/recovery terverifikasi. MCP/skills executable tetap dijadwalkan pada fase berikutnya.

## Phase 2 — Alur bisnis deterministik dan reference outcomes

- [ ] Bangun reference assistant untuk mencari pelanggan, meninjau peluang sales, dan menyiapkan draft quotation atau activity.
- [ ] Tentukan versi/edition Odoo serta model/API yang benar-benar tersedia; dokumentasikan pilihan sebelum implementasi adapter.
- [ ] Pisahkan tool read, prepare, dan execute; tool tidak menyediakan arbitrary SQL, arbitrary model method, atau unrestricted URL.
- [ ] Approval terikat payload, actor, tenant, dan versi record. Perubahan payload atau record membatalkan approval lama.
- [ ] Tangani pagination, rate limit, timeout, partial failure, retry, dan read-back hasil. Jangan menganggap semua endpoint mendukung idempotency native.
- [ ] Sediakan contract versioning dan compatibility fixtures untuk consumer proyek lain.

**Gate:** happy path, exception, approval, dan recovery bisa diuji dengan data referensi tanpa bergantung pada kualitas LLM. Expected outcomes ditulis dari aturan dan sumber, bukan disalin dari output model.

## Phase 3 — AI assistant dan reusable skills

- [ ] Implementasikan assistant dan kontrak skills di AI-AGENTS.md serta REUSABLE-SKILLS.md, dengan structured outputs dan tool allowlist.
- [ ] Implementasikan provider interface OpenAI, Claude, Grok; contract test semuanya dan jalankan canary nyata terpisah dengan data yang diizinkan bila credentials tersedia.
- [ ] Tambahkan local inference Ollama dan evaluasi jalur lokal; aturan offline/private mengikuti LOCAL-AI-AND-PROVIDERS.md.
- [ ] Tambahkan retrieval sumber kerja yang relevan dan pemeriksaan unsupported claims. AI mengusulkan; domain service menegakkan izin, state, dan aturan.
- [ ] Versikan prompt/model/skill/schema; simpan latency, usage, biaya dan outcome. Missing usage tidak dilaporkan sebagai biaya nol.

**Gate:** satu tugas lengkap berjalan memakai AI, output malformed/unsupported diblokir, skills dapat dipakai ulang oleh assistant dan automation worker. Provider yang belum diuji nyata tidak diberi label live-validated.

## Phase 4 — Custom MCP server

- [ ] Implementasikan tools TypeScript sesuai MCP-INTEGRATIONS.md: read → prepare → approved execute → verify.
- [ ] Buat reference client yang benar-benar memanggil MCP melalui protocol; jangan hanya memanggil fungsi tool langsung dalam unit test.
- [ ] Tegakkan authentication, tenant scope, role, approval, limits, dan sanitized tool responses di server.
- [ ] Uji schema/protocol, timeout, cancellation, malformed calls, tool injection, stale approval, dan duplicate execution.

**Gate:** assistant menyelesaikan satu tugas melalui MCP dengan final state terverifikasi; request tanpa hak ditolak meskipun prompt memerintahkannya.

## Phase 5 — Business platform dan automation terhubung

- [ ] Gunakan worker/scheduler atau integrasi yang dipilih untuk workflow utama. Selesaikan release utama tanpa n8n; extension yang belum dipilih bukan pekerjaan wajib.

- [ ] Hubungkan Odoo menggunakan kontrak pada BUSINESS-PLATFORM.md; identitas record dan source of truth harus eksplisit.
- [ ] Jalankan alur read/propose/approve/write/read-back pada sandbox atau platform lokal; fake dipakai untuk failure injection, bukan pengganti bukti connected integration.
- [ ] Tambahkan satu trigger automation terjadwal/event-based, dengan checkpoint, retry, dead-letter/review queue, dan idempotency.
- [ ] Pastikan update eksternal, expired credentials, rate limit, duplicate events, dan unknown outcomes memiliki jalan pemulihan.
- [ ] Siapkan konfigurasi tenant/business kedua sebagai bukti solusi tidak hanya cocok untuk seed demo pertama.

**Gate:** perubahan di platform tujuan terbukti benar; replay tidak menggandakan efek; akses sandbox yang belum tersedia tetap menjadi dependency terbuka.

## Phase 6 — Evaluasi kualitas dan nilai pekerjaan

- [ ] Bekukan development/regression set dan held-out set terpisah berdasarkan keluarga kasus/sumber; variasi dari template sama tidak dibagi untuk menciptakan holdout semu.
- [ ] Tentukan rubric, denominator, target kualitas per risiko, dan jumlah kasus per kategori sebelum final run. Laporkan jumlah, coverage, dan ketidakpastian, bukan persentase saja.
- [ ] Jalankan seluruh failure scenarios pada SECURITY-TESTING-MONITORING.md; gunakan production code paths untuk evaluasi end-to-end.
- [ ] Bandingkan manual workflow dengan assisted workflow pada tugas setara dan correctness sama; catat active work time, waiting time, corrections, serta total elapsed.
- [ ] Labelkan single-operator/synthetic/sandbox sesuai kondisi. Tidak perlu meminta orang mencoba demo; hasil mandiri tidak disebut customer ROI.
- [ ] Uji model/prompt/skill atau aturan bisnis versi baru dan bandingkan regresi. Jika holdout dipakai debugging, jadikan regression set dan siapkan holdout baru untuk klaim generalisasi.

**Metrik proyek:** tool task success; correct record selection; unauthorized-write rejection; duplicate effects; proposal correctness; p95 tool execution; verified operations per minute; biaya per tugas benar.

**Gate:** laporan bisa direproduksi dengan dataset/version/run ID; semua critical controls lulus pada suite yang dinyatakan; quality thresholds tercapai atau limitations/scope diperbaiki dan diuji ulang.

## Phase 7 — Reliability, security, dan performance lokal

- [ ] Jalankan API/UI/MCP/worker permission tests: beda role, beda tenant, direct API bypass, secret/PII leakage, serta prompt injection.
- [ ] Uji concurrency, interrupted worker, delayed callback, retry, unknown outcome, queue backlog, database recovery, dan backup/restore terisolasi.
- [ ] Ukur p50/p90/p95/p99 per operasi dan per alur end-to-end, dengan sample count, error rate, achieved throughput, dropped work, resources, dan correctness.
- [ ] Pisahkan waktu HTTP acknowledgement, queue wait, inference, downstream action, dan hasil terverifikasi. Fast failure/conflict tidak disamakan dengan pekerjaan selesai.
- [ ] Jalankan beban normal/peak/soak yang ditentukan dari workload V1 dan hardware tercatat; bounded real-provider canary terpisah dari beban synthetic/stub.
- [ ] Buktikan alert dipicu dan diterima pada test incident; uji release rollback serta runbook troubleshooting.

**Gate:** local release candidate lulus quality/reliability gates. Tes cloud-only existing tidak dipaksa dijalankan lokal; validasi cloud tersebut menunggu fase 9. Laporan lokal tidak diberi label cloud/production traffic.

## Phase 8 — Delivery pack dan release siap deploy

- [ ] Selesaikan panduan manusia di PROJECT-DELIVERY.md: install, daily use, approval, failure handling, backup, upgrade, dan support.
- [ ] Rekam demo dengan kasus normal, blocked/ambiguous, dan recovery; simpan acceptance checklist dan bukti hasil platform.
- [ ] Bekukan release commit, dependency versions, migration plan, rollback, konfigurasi, model licenses, dan sanitized evidence manifest.
- [ ] Siapkan rencana/IaC cloud, least-privilege access, resource/cost limits, alerts, secret management, backup dan teardown; jangan provision dahulu.
- [ ] Tentukan owner operasional, jadwal review kualitas, incident response, dan backlog improvement. Dokumentasi untuk operator tersedia dalam English; developer notes boleh Indonesia.

**Gate:** aplikasi dapat dipakai dan dipulihkan lokal mengikuti dokumen; semua prerequisite deployment tercatat; bukti release cocok dengan snapshot kode yang akan dideploy.

## Phase 9 — Deployment cloud TERAKHIR, validasi runtime, dan ongoing support

Target: **Azure**. Proyek 07 tetap punya deliverable offline mandiri; deployment private-cloud hanya varian tambahan, bukan syarat agar mode offline bekerja.

- [ ] Setelah fase 0–8 lulus, provision environment terisolasi, deploy immutable image, jalankan migrations, secret/network policies, dan health checks.
- [ ] Ulangi connected end-to-end acceptance di runtime cloud, termasuk authorization dan hasil platform; jangan menyalin hasil lokal sebagai bukti cloud.
- [ ] Jalankan workload cloud normal/peak/soak, failure recovery, queue/concurrency, delivered alerts, backup/restore terisolasi, dan rollback sesuai kontrak beban.
- [ ] Verifikasi provenance release, data retention, resource/cost caps, serta teardown; dokumentasikan resource yang sengaja dipertahankan.
- [ ] Perbarui operator handover dengan URL/environment/owner dan bukti runtime. Mulai cadence pemantauan, incident response, quality regression, serta evaluasi sebelum setiap perubahan.
- [ ] Tandai completed hanya jika acceptance cloud yang dipilih terpenuhi; bila tidak dideploy, status jujur local-ready/cloud-pending atau offline-delivered untuk 07.

**Gate akhir:** deployment dan hasil bisnis terverifikasi pada environment yang dinyatakan; rollback/recovery terbukti; owner support, monitoring, dan batas klaim jelas. Ongoing improvement berada dalam fase ini, bukan fase deployment lain di tengah rencana.
