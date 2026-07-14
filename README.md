# 9router Prefix Grouper

Script untuk mengelompokkan semua node provider/model di **9router** berdasarkan
field `prefix` (contoh: `hcnsec/*`, `nous/*`, `oc/*`).

9router menyimpan konfigurasi tiap provider di tabel `providerNodes` (SQLite),
di mana kolom `data` berisi JSON dengan field `prefix`. Script ini membaca DB
tersebut dan mencetak tampilan terkelompok yang rapi — berguna untuk audit
prefix mana yang sudah terdaftar dan provider apa yang memetakan ke masing-masing.

## Install

```bash
git clone https://github.com/cilokesteh/9router-prefix-groups.git
cd 9router-prefix-groups
# butuh python3 stdlib saja (sqlite3, json, argparse) — gak perlu pip install
```

## Usage

```bash
# Tampilan tabel (default)
python3 group_by_prefix.py

# Output JSON
python3 group_by_prefix.py --json

# Filter satu prefix
python3 group_by_prefix.py --prefix hcnsec

# DB custom
python3 group_by_prefix.py --db /path/to/data.sqlite
```

DB default: `~/.9router/db/data.sqlite`

## Contoh Output

```
🔹 Prefix: bluesminds  (1 node)
────────────────────────────────────────────────────────────
  • bluesminds     [openai-compatible]
      baseUrl : https://api.bluesminds.com/v1
      apiType : chat

🔹 Prefix: hcnsec  (1 node)
────────────────────────────────────────────────────────────
  • hcnsec        [openai-compatible]
      baseUrl : https://api.hcnsec.cn/v1
      apiType : chat

🔹 Prefix: oc  (1 node)
────────────────────────────────────────────────────────────
  • Opencode      [openai-compatible]
      baseUrl : https://opencode.ai/zen/v1
      apiType : chat

✅ Total: 3 nodes, 3 prefixes
```

## Catatan

- Script read-only — tidak mengubah DB 9router.
- Butuh akses baca ke file DB 9router (pastikan user punya permission).
