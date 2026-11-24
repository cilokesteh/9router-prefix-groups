# 9router Provider & Model Manager

Tool CLI untuk mengelola dan memetakan model 9Router (serta Nous Portal / Hermes) dengan hierarki terstruktur:

```
🏢 Provider  (e.g. Antigravity, Hcnsec, OpenCode)
   📁 Prefix  (e.g. ag, hcnsec, oc)
      • Model  (e.g. ag/gemini-3.8-flash, hcnsec/DeepSeek-V4-Flash)
```

## Fitur Utama

| Perintah | Fungsi |
|---|---|
| `python3 group_by_prefix.py` | Tampilkan hierarki lengkap **Provider → Prefix → Model** dari 9Router |
| `--probe` | Real chat-probe ke setiap model via router (uji liveness nyata + latency ms) |
| `--live-only` | Filter hanya model yang statusnya `LIVE` (harus bersama `--probe`) |
| `--prefix SUB` | Filter berdasarkan nama provider atau prefix substring |
| `--source portal` | Ambil katalog dari Nous Portal API (`free`/`paid`, `context_length`) |
| `--source both` | Gabungkan 9Router + Nous Portal |
| `--json` | Output terstruktur format JSON (untuk bot / dashboard) |
| `--registry` | List semua provider yang didukung (40+ prefix) |
| `--add PREFIX --apikey KEY` | Tambah provider baru + API key langsung ke database SQLite 9Router |

## Instalasi

```bash
git clone https://github.com/cilokesteh/9router-prefix-groups.git
cd 9router-prefix-groups
# Standar library Python saja — tanpa dependensi pip tambahan
```

## Penggunaan

```bash
# 1. Tampilkan semua model terkelompok rapi (Provider → Prefix → Model)
python3 group_by_prefix.py

# 2. Probe liveness model secara real-time via 9Router
python3 group_by_prefix.py --probe

# 3. Tampilkan hanya model yang aktif (LIVE)
python3 group_by_prefix.py --probe --live-only

# 4. Filter satu prefix saja (contoh: ag atau hcnsec)
python3 group_by_prefix.py --prefix ag

# 5. Cek registry semua provider yang didukung
python3 group_by_prefix.py --registry

# 6. Tambah provider & API key ke 9Router
python3 group_by_prefix.py --add deepseek --apikey sk-xxx...

# 7. Output JSON
python3 group_by_prefix.py --json
```

## Contoh Output

```text
# Model Inventory (Provider → Prefix → Model)  (2026-11-24 08:24)
3 providers · 3 prefixes · 40 models

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏢 Provider: Antigravity
   Keys: 4/4 active · BaseURL: -
────────────────────────────────────────────────────────────────────
  📁 Prefix: ag (19 models)
     • ag/claude-opus-4-6-thinking              [Vision] [ctx: 200,000]
     • ag/claude-opus-5-5-max                   [Vision] [ctx: 1,000,000]
     • ag/claude-sonnet-4-6                     [Vision] [ctx: 1,000,000]
     • ag/claude-sonnet-5-5-max                 [Vision] [ctx: 1,000,000]
     • ag/gemini-3.8-flash                      [Vision] [ctx: 1,048,576]
     • ag/gemini-3.8-flash-high                 [Vision] [ctx: 1,048,576]
     ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏢 Provider: Hcnsec
   Keys: 3/3 active · BaseURL: https://api.hcnsec.cn/v1
────────────────────────────────────────────────────────────────────
  📁 Prefix: hcnsec (12 models)
     • hcnsec/DeepSeek-V4-Flash                 [ctx: 1,000,000]
     • hcnsec/MiniMax-M3.1-Flash                [Vision] [ctx: 1,000,000]
     • hcnsec/Qwen3.8-27B                       [ctx: 262,144]
     • hcnsec/Qwen3.8-Flash-Next                [ctx: 262,144]
     • hcnsec/auto                              [ctx: 200,000]
     • hcnsec/glm-5.3                           [ctx: 1,000,000]
     ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏢 Provider: OpenCode Zen
   Keys: live catalog · BaseURL: -
────────────────────────────────────────────────────────────────────
  📁 Prefix: oc (9 models)
     • oc/beam-free                             [ctx: 1,048,576]
     • oc/deepseek-v4.1-flash-free              [ctx: 200,000]
     • oc/flint-40b-free                        [ctx: 262,144]
     • oc/hy4-flash-free                        [ctx: 1,048,576]
     ...
```

## Catatan
- **Read-only saat default**: Tidak mengubah isi database SQLite 9Router kecuali menggunakan perintah `--add`.
- **Merge Otomatis**: Secara otomatis menggabungkan database lokal dengan endpoint `/v1/models` dari service 9Router yang sedang berjalan.
- **Hierarki Jelas**: Model selalu dikelompokkan secara konsisten: **Provider → Prefix → Model**.
