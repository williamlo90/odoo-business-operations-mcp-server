# Project Delivery — Panduan untuk Manusia

Proyek 02: **Odoo Business Operations MCP Server**

Tanggal rencana: 2026-10-08. Status: **Phase 0–2 selesai; alur deterministik Odoo lokal terimplementasi dan diuji. Phase 3 implementasi offline selesai; Phase 4–10 belum selesai**. Checklist hanya dicentang setelah artefak dan verifikasinya tersedia.

## Penjelasan satu kalimat

Memberi assistant akses yang terbatas dan dapat diaudit untuk membaca data Odoo serta menyiapkan perubahan bisnis tanpa akses database bebas.

**Siapa yang memakai:** Sales operations dan administrator Odoo.

**Pekerjaan sehari-hari:** Permintaan operator → assistant memilih skill → tools membaca Odoo → proposal perubahan → preview → approval → eksekusi → read-back Odoo → receipt dan audit.

## Demo penerimaan

Assistant menyiapkan draft quotation dari record Odoo; operator melihat preview lalu menyetujui; read-back membuktikan hanya satu draft benar terbentuk meski request diulang.

Demo menggunakan data sintetis/test tenant. Tunjukkan input, bukti, keputusan, tindakan, hasil, dan cara menangani kegagalan. Jangan hanya memperlihatkan chat yang menjawab dengan lancar.

## Dokumen delivery yang dibuat saat implementasi

- [ ] Business brief satu halaman: masalah, owner, scope, hasil yang diukur, dan batas kemampuan.
- [ ] Quick start: prerequisites, install lokal, seed demo, login roles, startup/shutdown, dan uninstall/cleanup.
- [ ] User guide berbahasa English: langkah penggunaan dengan contoh dan screenshot, istilah sederhana, arti setiap status, serta kapan harus meminta bantuan.
- [ ] Acceptance checklist: tugas, hasil yang diharapkan, hasil aktual, evidence, pass/fail; bisa dijalankan sendiri tanpa merekrut demo tester.
- [ ] Runbook operator: kegagalan umum, langkah diagnosis, pemulihan, eskalasi, backup/restore, serta rollback.
- [ ] Release/evidence manifest: commit, data/model/config versions, tests, integrations yang benar-benar diuji, limitations yang relevan.
- [ ] Demo singkat dan case study dengan hasil terukur yang benar; single-operator/synthetic tetap dinyatakan sesuai lingkup.
- [ ] Handover: pemilik credentials/config, permissions, biaya operasi/asumsi, retention, support owner, dan jadwal pemeliharaan.
- [ ] Cloud deployment appendix setelah Phase 10: environment, health, monitoring, recovery proof, teardown/ongoing ownership.

## Ongoing support

- Periksa failed jobs, unknown outcomes, stale sync, resource/cost alerts dan review queues pada cadence yang sesuai beban.
- Review feedback/error clusters dan tambahkan regression cases setelah insiden.
- Setiap perubahan prompt/model/skill/policy/platform API memicu pengujian yang relevan sebelum release.
- Perbarui dokumen dan runbook agar sesuai aplikasi; simpan sejarah eksperimen lokal bila berguna, public narrative fokus hasil tervalidasi.

## Definisi selesai

Seorang operator dapat memahami manfaatnya, menjalankan tugas normal, mengenali kasus yang harus ditinjau, menemukan bukti hasil, dan mengikuti pemulihan menggunakan dokumentasi. Local-ready, connected-sandbox-validated, offline-delivered, dan cloud-validated adalah status berbeda; hanya gunakan yang sudah dibuktikan.

## Delivery automation

- [ ] Dokumentasikan worker/API/scheduler utama, recovery dan ownership; buktikan install dan workflow tanpa n8n.
- [ ] Extension automation hanya memiliki export/demo tambahan jika dipilih; tidak menjadi syarat delivery utama.
