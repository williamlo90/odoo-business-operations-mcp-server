# V1 acceptance cases

Specification v0.1, 2026-10-08. Expected outcomes ditetapkan sebelum implementasi. Status dan batas coverage terbaru
tercantum pada [Phase 2](PHASE-2.md); ini bukan dataset evaluasi kualitas Phase 7.

Fixture awal: company A/B; operator, approver, admin dan auditor terpisah;
dua customer bernama sama dengan ID berbeda; opportunity per company;
produk P1 = IDR 100,000/unit dan P2 = IDR 50,000/unit, tanpa pajak/diskon.
Pesanan 2 × P1 + 1 × P2 harus total IDR 250,000. Nilai ini ditetapkan dari
aturan fixture, bukan output model. Semua nama/record sintetis.

| ID | Trigger / kondisi | Expected outcome |
| --- | --- | --- |
| A01 | Cari customer unik yang diizinkan | ID dan company benar, source reference tersedia, tanpa write |
| A02 | Dua customer bernama sama | Minta pilihan eksplisit; tidak memilih otomatis atau membuat quotation |
| A03 | Baca customer/opportunity company B sebagai actor A | Ditolak di service, API dan MCP; data B tidak bocor |
| A04 | Baca opportunity valid | Customer, stage dan owner cocok sumber; tanpa write |
| A05 | Prepare 2 × P1 + 1 × P2 | Preview IDR 250,000 dengan currency/items/customer/company benar; belum ada draft Odoo |
| A06 | Approver berwenang menyetujui A05, execute | Tepat satu draft quotation; lines/qty/prices/total/customer/company sesuai; receipt berisi ID dan read-back |
| A07 | Write tanpa approval / approval expired / admin tanpa role approver | Ditolak sebelum external write, audit alasan |
| A08 | Payload atau tenant/actor diganti memakai approval lama | Ditolak; perlu proposal/approval sesuai konteks baru |
| A09 | Record/pricing berubah setelah preview, termasuk race saat execute | Approval lama tidak menghasilkan draft berdasarkan data usang; minta preview/approval baru |
| A10 | Request diulang atau dua execute bersamaan | Satu external effect dan operation outcome konsisten; hitung final records, bukan hanya HTTP status |
| A11 | Odoo membuat draft lalu response timeout | Status unknown; lookup operation reference; temukan satu draft, read-back lalu verified; tanpa blind retry |
| A12 | Odoo gagal sebelum write / 429 / credential expired | Error terklasifikasi; bounded retry hanya jika aman; tidak ada false success |
| A13 | Pagination beberapa halaman | Tidak ada record hilang/duplikat pada fixture tetap; perubahan sumber dideteksi/ditangani sesuai kontrak |
| A14 | Tool injection meminta model/field/URL terlarang | Allowlist menolak, tanpa kebocoran/side effect |
| A15 | Qty invalid, produk inactive, currency atau tax policy unsupported | Prepare ditolak dengan alasan; tidak ada approval/write |
| A16 | Follow-up activity valid lalu approve | Tepat satu activity pada opportunity/company, assignee dan due date yang benar; read-back |
| A17 | Read-back belum tersedia atau berbeda dari proposal | Tidak berstatus verified; unknown/review dengan alasan dan recovery |
| A18 | Restart worker setelah dispatch | Durable state direkonsiliasi; tidak membuat draft kedua |
| A19 | Akun tanpa login atau scope dari prompt yang dimanipulasi | Server menolak; scope berasal dari authenticated identity |
| A20 | Konfigurasi business/company kedua | Skills yang sama bekerja dengan data/policy kedua tanpa menyalin core logic |

Setiap run kelak menyimpan case ID, code revision, fixture version, expected/actual,
pass/fail, correlation/operation/approval IDs, external ID, jumlah efek, timestamp
dan evidence path yang disanitasi. A06/A09/A10/A11/A16 memerlukan bukti Odoo nyata
untuk connected acceptance; fake hanya untuk failure injection.

Gate kritis: seluruh kasus izin, stale approval, duplicate effect dan false-success
yang tercantum harus lulus. Target kualitas AI, workload dan held-out evaluation
ditetapkan terpisah sebelum final run Phase 7.
