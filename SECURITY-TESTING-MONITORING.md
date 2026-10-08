# Access Control, Testing, Monitoring & Documentation

Proyek 02: **Odoo Business Operations MCP Server**

Tanggal rencana: 2026-10-08. Status: **Phase 0-8 selesai untuk scope lokal terpilih; Phase 9-10 belum selesai**. Claude/Grok opsional dan belum live-validated. Evaluasi Phase 7 adalah regresi sintetis; bukan klaim generalisasi atau ROI manusia.

## Access control sejak awal

| Role | Izin minimum |
| --- | --- |
| Operator | Membaca scope sendiri, menjalankan assistant, membuat proposal |
| Approver | Menyetujui tindakan dalam batas kewenangan; approval terikat payload/version |
| Administrator | Mengelola koneksi, policy, roles, model/runtime; tidak otomatis memperoleh hak approval bisnis |
| Auditor | Membaca audit/evidence yang disanitasi; tidak mengeksekusi action |
| Worker/service account | Hanya skill/tools dan tenant yang ditugaskan |

Pisahkan tenant dan object-level authorization pada API, MCP, workers, retrieval, cache, export, dan logs. Untuk tindakan penting terapkan pemisahan pengusul/approver sesuai policy. Test environment tidak mengakses data produksi dan destructive tests hanya ke database disposable.

## Kasus wajib spesifik proyek

- [x] Dua customer bernama sama
- [x] Record antar-company tidak boleh tercampur
- [x] Approval dipakai ulang dengan payload berbeda
- [x] Record Odoo berubah setelah preview
- [x] Timeout setelah draft berhasil dibuat
- [x] Pagination menghasilkan record yang hilang/berulang
- [x] Tool injection meminta akses model atau field terlarang

Bukti Phase 7: 38 tes domain/PostgreSQL/Odoo, 20 tes live, dan 86 tes offline lulus. Mapping kasus ke test ada pada [laporan Phase 7](docs/PHASE-7.md). Fault injection dan hasil model dinilai terpisah. Phase 8 menambahkan 98 tes offline, 41 tes PostgreSQL/Odoo, 14 tes live serta load/recovery lokal; lihat [evidence Phase 8](docs/PHASE-8.md).

## Lapisan testing

- [x] Unit: aturan bisnis, schemas, matching/parsing, transitions, permissions, evaluator semantics.
- [x] Contract: provider, custom MCP protocol, platform API, migrations, skill versions.
- [x] Integration: PostgreSQL nyata terisolasi, queue/worker, approval/execute/verify, sandbox platform.
- [x] End-to-end: operator menjalankan client CLI sampai outcome tujuan; negative tests memanggil API langsung.
- [x] AI quality: frozen labels, regresi sintetis (tanpa klaim holdout independen), wrong/missing evidence, prompt injection, unsupported claims, abstention, regressions.
- [x] Reliability: duplicate events, lost response, concurrent writes, worker interruption, bounded request/queue limits dan memory caps (tanpa memaksa host OOM), restore dan rollback.

## KPI dan alat ukur

tool task success; correct record selection; unauthorized-write rejection; duplicate effects; proposal correctness; p95 tool execution; verified operations per minute; biaya per tugas benar.

Setiap report menyertakan code revision dan dirty diff fingerprint bila ada, dataset/version/hash, model/provider/runtime, environment/hardware, workload, durations, sample counts, excluded records beserta alasan, serta expected/observed results. Jangan menggabungkan benchmark berbeda menjadi satu persentase.

Tetapkan workload normal, peak, soak, batas error, resource budget, dan stop conditions sebelum run. p50/p90/p95/p99 dilaporkan per operasi dengan N dan distribusi status; satu upload bukan bukti distribusi tail latency. Ukur achieved rate/dropped work, queue wait, processing completion, dan correctness. Concurrency test harus membuktikan jumlah final effects yang tepat, bukan sekadar semua respons 200/409.

## Monitoring dan troubleshooting

- [x] Correlation ID API/MCP dan durasi Odoo; structured logs tanpa payload/credentials. Assistant traces menyimpan model latency, usage dan status; biaya tetap unknown tanpa rate card.
- [x] Metrik business per tenant: status operasi, jumlah proposal dan usia sejak update operasi unresolved. Queue counts/age tersedia pada monitor lokal.
- [x] Alert test: database outage memicu firing/recovery dan diterima receiver SQLite lokal. Tidak ada klaim email/Slack atau paging manusia.
- [x] Runbook untuk provider outage, expired credentials, stale source, stuck job, unknown write, restore, rollback dan duplicate incident.
- [x] Akses dan retention lokal dijelaskan dalam [runbook](docs/LOCAL-RUNBOOK.md); raw backup tetap ignored, evidence publik disanitasi.

Monitoring otomatis untuk spend, quality drift dan runtime cloud belum diimplementasikan; bukan bagian dari alert readiness/queue lokal. Tidak ada UI browser di scope ini.

## Release gate

- Nol bypass izin, cross-tenant leakage, duplicate side effect, dan false-success pada critical scenario suite yang ditetapkan. Nol pada suite terbatas tidak berarti jaminan nol di seluruh produksi.
- Quality thresholds ditentukan per risiko sebelum final evaluation; laporkan coverage serta kasus yang gagal.
- Local evidence lulus pada Phase 8; cloud-runtime evidence baru dijalankan pada Phase 10.
- Test yang gagal diselesaikan atau scope dikoreksi dan diverifikasi; tidak menurunkan gate diam-diam setelah melihat hasil.

## Acceptance automation yang dipilih

Release utama diuji tanpa n8n. Uji worker/scheduler/API yang benar-benar dipakai; n8n hanya memiliki acceptance tambahan jika extension secara eksplisit dipilih. Lihat [N8N-AUTOMATION.md](N8N-AUTOMATION.md).
