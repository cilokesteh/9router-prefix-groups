# 9router Provider Manager

Script untuk mengelola **9router provider nodes** — group by prefix, list, dan
add provider baru langsung ke DB.

## Fitur

| Perintah | Fungsi |
|----------|--------|
| `python3 group_by_prefix.py` | Group by prefix — **hanya tampilin provider yg punya API key valid** |
| `--registry` | List **semua provider** yg didukung 9router (32+ prefix, bukan cuma yg di DB) |
| `--add PREFIX --apikey KEY` | Tambah provider + API key langsung ke 9router DB |
| `--prefix PREFIX` | Filter tampilan utk 1 prefix aja |
| `--json` | Output JSON (buat scripting) |
| `--baseurl URL` | Base URL kustom (utk prefix custom di luar registry) |

## Cara Kerja

Baca tabel `providerNodes` + `providerConnections` dari SQLite DB 9router
(`~/.9router/db/data.sqlite`), JOIN dua tabel, dan tampilkan provider yang
memiliki API key aktif.

## Registry Provider

`--registry` nampilin semua provider yg didukung 9router (32 prefix):

**Chat:** hcnsec, kimi, minimax, openai, deepseek, groq, xai, mistral, qwen,
openrouter, nvidia, gemini, together, fireworks, cohere, anthropic, iflow,
perplexity, oc, bluesminds

**Embedding:** voyage, jina

**Image:** fal, stability, recraft

**TTS/STT:** elevenlabs, deepgram

**Web Search:** tavily, brave, serper, exa

## Install

```bash
git clone https://github.com/cilokesteh/9router-prefix-groups.git
cd 9router-prefix-groups
# stdlib only — no pip install needed
```

## Usage

```bash
# Group by prefix (default) — hanya yg ada API key
python3 group_by_prefix.py

# List semua provider yg didukung 9router
python3 group_by_prefix.py --registry

# Tambah provider baru + API key
python3 group_by_prefix.py --add deepseek --apikey sk-xxx...

# Filter satu prefix
python3 group_by_prefix.py --prefix hcnsec

# Output JSON
python3 group_by_prefix.py --json
```

## Contoh Output

```
🔹 hcnsec (GLM Coding (HCN))  [3 key(s)]
────────────────────────────────────────────────────────────
  ✅   active | sk-Cn5oI...znxG
  ✅   active | sk-27e8H...85uc
  ✅   active | sk-j9uhR...WBhZ
      baseUrl: https://api.hcnsec.cn/v1
      type:    chat

🔹 oc (OpenCode)  [4 key(s)]
────────────────────────────────────────────────────────────
  ✅   active | sk-c8KuD...NBNJ
  ✅   active | sk-jAjPX...fgyz
  ✅   active | sk-fdnZi...3wPF
  ✅   active | sk-aUlA3...mj9d
      baseUrl: https://opencode.ai/zen/v1
      type:    chat

✅ Total: 8 API keys across 3 providers (dengan key valid)
```

## Catatan

- **Read-only saat default** — tidak mengubah DB 9router.
- **`--add`** bisa nulis ke DB (tambah providerNode + providerConnection).
- Script cuma buat **provider tipe apikey** (bukan OAuth kayak Claude Code / GitHub Copilot).
- API key disimpan di tabel `providerConnections` — 9router akan auto-test saat request pertama.