# Phase Plan & Definition of Done

Proyek 02: **Odoo Business Operations MCP Server**

Tanggal rencana: 2026-10-08. Status: **Phase 0–2 selesai; alur deterministik Odoo lokal terimplementasi dan diuji. Phase 3–5 implementasi offline selesai; Phase 6–10 belum selesai**. Checklist hanya dicentang setelah artefak dan verifikasinya tersedia.

Urutan wajib: **0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10**. Access control dan test dimulai saat feature dibuat; fase 8 merupakan verifikasi menyeluruh, bukan pertama kali security ditambahkan. Tidak ada deployment aplikasi ke cloud sebelum fase 10.

Roadmap revisi: Phase 3–5 menyelesaikan implementasi dengan tes ringan; pengujian Docker, provider nyata dan model lokal dikumpulkan pada Phase 6. Satu phase implementasi = satu commit pembelajaran.

Pemakaian API model atau test tenant SaaS dari aplikasi lokal diperbolehkan pada fase integrasi. Itu berbeda dari deployment aplikasi kita ke cloud. Mode offline proyek 07 tetap tidak memakai API eksternal. Infrastructure-as-code boleh disiapkan sebelum fase 10 tanpa apply/provision.

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

- [x] Bangun reference assistant untuk mencari pelanggan, meninjau peluang sales, dan menyiapkan draft quotation atau activity.
- [x] Tentukan versi/edition Odoo serta model/API yang benar-benar tersedia; dokumentasikan pilihan sebelum implementasi adapter.
- [x] Pisahkan tool read, prepare, dan execute; tool tidak menyediakan arbitrary SQL, arbitrary model method, atau unrestricted URL.
- [x] Approval terikat payload, actor, tenant, dan versi record. Perubahan payload atau record membatalkan approval lama.
- [x] Tangani pagination, rate limit, timeout, partial failure, retry, dan read-back hasil. Jangan menganggap semua endpoint mendukung idempotency native.
- [x] Sediakan contract versioning dan compatibility fixtures untuk consumer proyek lain.

**Gate:** happy path, exception, approval, dan recovery bisa diuji dengan data referensi tanpa bergantung pada kualitas LLM. Expected outcomes ditulis dari aturan dan sumber, bukan disalin dari output model.

Evidence Phase 2 (2026-10-08): [delivery dan hasil verifikasi](docs/PHASE-2.md), [panduan Odoo](docs/ODOO-LOCAL.md), [kontrak v1](docs/CONTRACT-V1.md). 38 tests lulus, termasuk 9 connected cases Odoo nyata; fresh-volume install dan CLI quotation lulus. AI/MCP/worker tetap pada fase berikutnya.

## Phase 3 — Implementasi assistant AI dan reusable skills

- [x] Lengkapi empat executable skills, typed contracts, source retrieval dan output validation.
- [x] Implementasikan adapter OpenAI, Claude, Grok dan Ollama; uji format API, refusal, timeout dan local-only policy dengan HTTP simulasi.
- [x] Hubungkan client TypeScript dengan assistant Python untuk task, preview, clarification dan recovery.
- [x] Sediakan state task durable, replay yang aman, versi prompt/schema/skill, latency, token usage dan estimasi biaya berkonfigurasi.
- [x] Jalankan tes ringan termasuk identity/tenant scope, unsupported claims, malformed output, cancellation dan reuse lintas caller.

**Gate implementasi:** client dan assistant memakai production code paths dengan transport simulasi; semua tes offline phase lulus. Tidak membutuhkan Docker atau model nyata. Canary provider, provisioning Ollama dan penerimaan bisnis nyata menjadi gate Phase 6.

Evidence: [Phase 3](docs/PHASE-3.md), 49 tes Python dan 2 tes client antarp proses lulus.

## Phase 4 — Implementasi custom MCP server

- [x] Bangun tools TypeScript read → prepare → approved execute → verify dengan schemas dan SDK/protocol dipin.
- [x] Hubungkan reference client dan assistant melalui MCP stdio yang benar-benar berjalan antarp proses.
- [x] Tegakkan session identity, role, tenant scope, payload/approval constraints, limits, cancellation dan sanitized errors.
- [x] Uji protocol, malicious input, expired session, stale approval, concurrent/replayed execution dan unknown outcomes dengan domain HTTP simulasi.

**Gate implementasi:** percakapan MCP nyata melalui stdio dan alur assistant-to-MCP lulus; platform downstream disimulasikan. Validasi Odoo/PostgreSQL nyata tetap Phase 6.

Evidence: [Phase 4](docs/PHASE-4.md), 7 tes protocol antarp proses lulus.

## Phase 5 — Implementasi automation dan recovery

- [x] Tambahkan worker Python dan trigger terjadwal/event dengan handler skills yang sama.
- [x] Persist jobs, deduplication keys, checkpoints, retry backoff, lease, review/dead-letter state dan outcome.
- [x] Pisahkan approval manusia dari automation; jangan membuat approval atau blind retry write.
- [x] Uji duplicate events, restart, concurrent claim, expired credentials, unknown results dan isolasi tenant dengan storage lokal terisolasi.
- [x] Dokumentasikan ownership scheduler, state, recovery dan konfigurasi tenant kedua; n8n tetap bukan dependency.

**Gate implementasi:** worker/scheduler nyata memakai persistent storage ringan, production handlers dan HTTP simulasi; tes restart/dedup/isolation lulus. Database aplikasi dan Odoo tetap sumber kebenaran transaksi bisnis, local job store hanya menyimpan orchestration.

Evidence: [Phase 5](docs/PHASE-5.md), 16 tes worker dan 8 tes MCP termasuk worker CLI lintas proses lulus.

## Phase 6 — Integrasi nyata dan validasi gabungan

- [ ] Jadwalkan resource proyek ini; jalankan stack Docker secara terkendali tanpa mengganggu proyek lain.
- [ ] Ulangi regresi PostgreSQL/Odoo Phase 1–2, lalu sambungkan assistant, MCP dan worker.
- [ ] Jalankan canary nyata OpenAI, Claude dan Grok secara terpisah untuk credentials yang tersedia; catat status per provider.
- [ ] Provision/pin Ollama dan model/license/artifacts; uji inference, local-only policy, resource usage dan recovery nyata.
- [ ] Buktikan workflow AI → MCP → proposal → approval manusia → Odoo write → read-back; periksa efek duplikat, stale sources, timeout dan recovery.
- [ ] Buktikan skill reuse dan tenant kedua pada stack nyata; benahi masalah integrasi sebelum evaluasi kualitas.

**Gate integrasi:** hasil bisnis dan recovery benar-benar terverifikasi pada environment yang disebut. Simulasi tidak menggantikan bukti connected. Provider yang tidak tersedia tetap pending, tidak diberi label live-validated. Tahap ini dikerjakan sebelum evaluasi Phase 7.

## Phase 7 — Evaluasi kualitas dan nilai pekerjaan

- [ ] Bekukan development/regression set dan held-out set terpisah berdasarkan keluarga kasus/sumber; variasi dari template sama tidak dibagi untuk menciptakan holdout semu.
- [ ] Tentukan rubric, denominator, target kualitas per risiko, dan jumlah kasus per kategori sebelum final run. Laporkan jumlah, coverage, dan ketidakpastian, bukan persentase saja.
- [ ] Jalankan seluruh failure scenarios pada SECURITY-TESTING-MONITORING.md; gunakan production code paths untuk evaluasi end-to-end.
- [ ] Bandingkan manual workflow dengan assisted workflow pada tugas setara dan correctness sama; catat active work time, waiting time, corrections, serta total elapsed.
- [ ] Labelkan single-operator/synthetic/sandbox sesuai kondisi. Tidak perlu meminta orang mencoba demo; hasil mandiri tidak disebut customer ROI.
- [ ] Uji model/prompt/skill atau aturan bisnis versi baru dan bandingkan regresi. Jika holdout dipakai debugging, jadikan regression set dan siapkan holdout baru untuk klaim generalisasi.

**Metrik proyek:** tool task success; correct record selection; unauthorized-write rejection; duplicate effects; proposal correctness; p95 tool execution; verified operations per minute; biaya per tugas benar.

**Gate:** laporan bisa direproduksi dengan dataset/version/run ID; semua critical controls lulus pada suite yang dinyatakan; quality thresholds tercapai atau limitations/scope diperbaiki dan diuji ulang.

## Phase 8 — Reliability, security, dan performance lokal

- [ ] Jalankan API/UI/MCP/worker permission tests: beda role, beda tenant, direct API bypass, secret/PII leakage, serta prompt injection.
- [ ] Uji concurrency, interrupted worker, delayed callback, retry, unknown outcome, queue backlog, database recovery, dan backup/restore terisolasi.
- [ ] Ukur p50/p90/p95/p99 per operasi dan per alur end-to-end, dengan sample count, error rate, achieved throughput, dropped work, resources, dan correctness.
- [ ] Pisahkan waktu HTTP acknowledgement, queue wait, inference, downstream action, dan hasil terverifikasi. Fast failure/conflict tidak disamakan dengan pekerjaan selesai.
- [ ] Jalankan beban normal/peak/soak yang ditentukan dari workload V1 dan hardware tercatat; bounded real-provider canary terpisah dari beban synthetic/stub.
- [ ] Buktikan alert dipicu dan diterima pada test incident; uji release rollback serta runbook troubleshooting.

**Gate:** local release candidate lulus quality/reliability gates. Tes cloud-only existing tidak dipaksa dijalankan lokal; validasi cloud tersebut menunggu fase 10. Laporan lokal tidak diberi label cloud/production traffic.

## Phase 9 — Delivery pack dan release siap deploy

- [ ] Selesaikan panduan manusia di PROJECT-DELIVERY.md: install, daily use, approval, failure handling, backup, upgrade, dan support.
- [ ] Rekam demo dengan kasus normal, blocked/ambiguous, dan recovery; simpan acceptance checklist dan bukti hasil platform.
- [ ] Bekukan release commit, dependency versions, migration plan, rollback, konfigurasi, model licenses, dan sanitized evidence manifest.
- [ ] Siapkan rencana/IaC cloud, least-privilege access, resource/cost limits, alerts, secret management, backup dan teardown; jangan provision dahulu.
- [ ] Tentukan owner operasional, jadwal review kualitas, incident response, dan backlog improvement. Dokumentasi untuk operator tersedia dalam English; developer notes boleh Indonesia.

**Gate:** aplikasi dapat dipakai dan dipulihkan lokal mengikuti dokumen; semua prerequisite deployment tercatat; bukti release cocok dengan snapshot kode yang akan dideploy.

## Phase 10 — Deployment cloud TERAKHIR, validasi runtime, dan ongoing support

Target: **Azure**. Proyek 07 tetap punya deliverable offline mandiri; deployment private-cloud hanya varian tambahan, bukan syarat agar mode offline bekerja.

- [ ] Setelah fase 0–9 lulus, provision environment terisolasi, deploy immutable image, jalankan migrations, secret/network policies, dan health checks.
- [ ] Ulangi connected end-to-end acceptance di runtime cloud, termasuk authorization dan hasil platform; jangan menyalin hasil lokal sebagai bukti cloud.
- [ ] Jalankan workload cloud normal/peak/soak, failure recovery, queue/concurrency, delivered alerts, backup/restore terisolasi, dan rollback sesuai kontrak beban.
- [ ] Verifikasi provenance release, data retention, resource/cost caps, serta teardown; dokumentasikan resource yang sengaja dipertahankan.
- [ ] Perbarui operator handover dengan URL/environment/owner dan bukti runtime. Mulai cadence pemantauan, incident response, quality regression, serta evaluasi sebelum setiap perubahan.
- [ ] Tandai completed hanya jika acceptance cloud yang dipilih terpenuhi; bila tidak dideploy, status jujur local-ready/cloud-pending atau offline-delivered untuk 07.

**Gate akhir:** deployment dan hasil bisnis terverifikasi pada environment yang dinyatakan; rollback/recovery terbukti; owner support, monitoring, dan batas klaim jelas. Ongoing improvement berada dalam fase ini, bukan fase deployment lain di tengah rencana.
