# Access Control, Testing, Monitoring & Documentation

Proyek 02: **Odoo Business Operations MCP Server**

Tanggal rencana: 2026-10-08. Status: **Phase 0-7 selesai untuk scope lokal terpilih; Phase 8-10 belum selesai**. Claude/Grok opsional dan belum live-validated. Evaluasi Phase 7 adalah regresi sintetis; bukan klaim generalisasi atau ROI manusia.

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

Bukti Phase 7: 38 tes domain/PostgreSQL/Odoo, 20 tes live, dan 86 tes offline lulus. Mapping kasus ke test ada pada [laporan Phase 7](docs/PHASE-7.md). Fault injection dan hasil model dinilai terpisah; reliability/load menyeluruh tetap Phase 8.

## Lapisan testing

- [ ] Unit: aturan bisnis, schemas, matching/parsing, transitions, permissions, evaluator semantics.
- [ ] Contract: provider, custom MCP protocol, platform API, migrations, skill versions.
- [ ] Integration: PostgreSQL nyata terisolasi, queue/worker, approval/execute/verify, sandbox platform.
- [ ] End-to-end: operator menjalankan UI/client sampai outcome tujuan; negative tests memanggil API langsung.
- [ ] AI quality: frozen labels, held-out cases, wrong/missing evidence, prompt injection, unsupported claims, abstention, regressions.
- [ ] Reliability: duplicate events, lost response, concurrent writes, worker interruption, resource exhaustion, restore dan rollback.

## KPI dan alat ukur

tool task success; correct record selection; unauthorized-write rejection; duplicate effects; proposal correctness; p95 tool execution; verified operations per minute; biaya per tugas benar.

Setiap report menyertakan code revision dan dirty diff fingerprint bila ada, dataset/version/hash, model/provider/runtime, environment/hardware, workload, durations, sample counts, excluded records beserta alasan, serta expected/observed results. Jangan menggabungkan benchmark berbeda menjadi satu persentase.

Tetapkan workload normal, peak, soak, batas error, resource budget, dan stop conditions sebelum run. p50/p90/p95/p99 dilaporkan per operasi dengan N dan distribusi status; satu upload bukan bukti distribusi tail latency. Ukur achieved rate/dropped work, queue wait, processing completion, dan correctness. Concurrency test harus membuktikan jumlah final effects yang tepat, bukan sekadar semua respons 200/409.

## Monitoring dan troubleshooting

- [ ] Correlation ID dari request sampai outcome; structured logs dengan redaction; metrics untuk errors, queue age, stale sync, model/schema failure, latency, resource usage, dan cost.
- [ ] Business metrics untuk verified completion, review/escalation, false closure/false hold jika relevan, dan perubahan kualitas per versi.
- [ ] Alert test: trigger incident terkontrol, buktikan notification diterima, dan dokumentasikan tindakan operator.
- [ ] Runbook untuk provider outage, expired platform token, failed sync, stuck job, unknown write, database restore, model rollback, dan duplicate incident.
- [ ] Retention dan akses logs/evidence/feedback jelas; raw sensitif disimpan terbatas, public evidence disanitasi.

## Release gate

- Nol bypass izin, cross-tenant leakage, duplicate side effect, dan false-success pada critical scenario suite yang ditetapkan. Nol pada suite terbatas tidak berarti jaminan nol di seluruh produksi.
- Quality thresholds ditentukan per risiko sebelum final evaluation; laporkan coverage serta kasus yang gagal.
- Local evidence lulus pada Phase 8; cloud-runtime evidence baru dijalankan pada Phase 10.
- Test yang gagal diselesaikan atau scope dikoreksi dan diverifikasi; tidak menurunkan gate diam-diam setelah melihat hasil.

## Acceptance automation yang dipilih

Release utama diuji tanpa n8n. Uji worker/scheduler/API yang benar-benar dipakai; n8n hanya memiliki acceptance tambahan jika extension secara eksplisit dipilih. Lihat [N8N-AUTOMATION.md](N8N-AUTOMATION.md).
