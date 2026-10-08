# Phase 0 environment evidence

Run `phase0-20261008-01`, 2026-10-08 Asia/Jakarta. Pemeriksaan read-only;
tidak memasang software, menjalankan container, memanggil model berbayar atau
mengubah environment/proyek lain.

| Pemeriksaan | Observasi |
| --- | --- |
| Project file inventory | 10 planning Markdown files; tidak ada source executable; tidak ditemukan AGENTS.md tambahan di subtree |
| `git -C <project> status --short` | Fatal not a git repository; shell pemeriksaan melaporkan exit code 1 |
| `git --version` | 2.45.1.windows.1 |
| `python --version` | 3.13.6 |
| `node --version` / `npm.cmd --version` | v22.19.0 / 11.17.0 |
| `docker version --format '{{json .}}'` | Client 29.8.0, desktop-linux; Server null; named pipe dockerDesktopLinuxEngine tidak tersedia |
| `docker compose version` | v5.5.1 |
| `docker ps -a` | Gagal terhubung; daftar container/image existing belum diketahui |
| `wsl --list --verbose` | Ubuntu, docker-desktop, podman-machine-default: WSL2, stopped |
| CIM CPU / physical memory | Intel Core i7-13620H; 16,868,962,304 bytes (~15.71 GiB) |
| `nvidia-smi --query-gpu=name,memory.total --format=csv,noheader` | RTX 4050 Laptop GPU, 6141 MiB; dipakai sebagai sumber VRAM, bukan CIM AdapterRAM yang terpotong |
| `Get-Command ollama` | Tidak ditemukan di PATH; tidak membuktikan tidak terpasang di lokasi lain |
| Selected process environment names | ODOO_URL, ODOO_DATABASE, ODOO_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, XAI_API_KEY, OLLAMA_HOST: semuanya tidak terisi pada process ini |

Nilai credentials tidak dibaca ke output; tidak mencari secret di proyek lain.
Baseline dokumen sebelum edit dicatat di `phase0-baseline.json`. Tidak ada source
revision karena Git belum diinisialisasi. Bukti hanya untuk lingkungan saat diperiksa.

Referensi Odoo: hasil pencarian dokumentasi resmi JSON-2 dan source install 19.0
tersedia; full-page fetch JSON-2 timeout dua kali. Source LICENSE resmi berhasil
dibaca. Detail endpoint, module availability dan compatibility belum diuji terhadap
instance lokal, sehingga tetap tercatat pada dependency D03/D06.
