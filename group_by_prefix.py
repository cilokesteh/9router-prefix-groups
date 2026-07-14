#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
9router Provider Manager — Group, List & Add Providers
=======================================================
Group all 9router provider/model nodes by their prefix, showing only
providers with VALID API keys. Supports adding new providers.

Usage:
    python3 group_by_prefix.py              # group by prefix (hanya yg ada apikey)
    python3 group_by_prefix.py --registry   # list semua provider yg didukung 9router
    python3 group_by_prefix.py --add hcnsec --apikey sk-xxx...   # add provider
    python3 group_by_prefix.py --json       # JSON output
    python3 group_by_prefix.py --prefix oc  # filter prefix
"""
import argparse
import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone

DEFAULT_DB = os.path.expanduser("~/.9router/db/data.sqlite")

# ─── PROVIDER REGISTRY ────────────────────────────────────────────────
# Semua OpenAI-compatible provider yang didukung 9router.
# Hanya provider dengan API key valid yang akan muncul di tampilan default.
PROVIDER_REGISTRY = {
    # ── API Key Providers (Chat/LLM) ──
    "hcnsec":     {"name": "GLM Coding (HCN)",       "baseUrl": "https://api.hcnsec.cn/v1",              "apiType": "chat"},
    "kimi":       {"name": "Kimi",                   "baseUrl": "https://api.moonshot.cn/v1",            "apiType": "chat"},
    "minimax":    {"name": "MiniMax",                "baseUrl": "https://api.minimax.chat/v1",           "apiType": "chat"},
    "openai":     {"name": "OpenAI",                 "baseUrl": "https://api.openai.com/v1",             "apiType": "chat"},
    "deepseek":   {"name": "DeepSeek",               "baseUrl": "https://api.deepseek.com/v1",            "apiType": "chat"},
    "groq":       {"name": "Groq",                   "baseUrl": "https://api.groq.com/openai/v1",        "apiType": "chat"},
    "xai":        {"name": "xAI Grok",               "baseUrl": "https://api.x.ai/v1",                   "apiType": "chat"},
    "mistral":    {"name": "Mistral",                "baseUrl": "https://api.mistral.ai/v1",              "apiType": "chat"},
    "qwen":       {"name": "Qwen (DashScope)",       "baseUrl": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1", "apiType": "chat"},
    "openrouter": {"name": "OpenRouter",             "baseUrl": "https://openrouter.ai/api/v1",           "apiType": "chat"},
    "nvidia":     {"name": "NVIDIA NIM",             "baseUrl": "https://integrate.api.nvidia.com/v1",    "apiType": "chat"},
    "gemini":     {"name": "Google Gemini",          "baseUrl": "https://generativelanguage.googleapis.com/v1beta/openai/", "apiType": "chat"},
    "together":   {"name": "Together AI",            "baseUrl": "https://api.together.xyz/v1",            "apiType": "chat"},
    "fireworks":  {"name": "Fireworks AI",           "baseUrl": "https://api.fireworks.ai/inference/v1",  "apiType": "chat"},
    "cohere":     {"name": "Cohere",                 "baseUrl": "https://api.cohere.com/v1",              "apiType": "chat"},
    "anthropic":  {"name": "Anthropic",              "baseUrl": "https://api.anthropic.com/v1",           "apiType": "chat"},
    "iflow":      {"name": "iFlow",                  "baseUrl": "https://inference.iflow.ai/v1",          "apiType": "chat"},
    "perplexity": {"name": "Perplexity",             "baseUrl": "https://api.perplexity.ai",              "apiType": "chat"},
    "oc":         {"name": "OpenCode",               "baseUrl": "https://opencode.ai/zen/v1",             "apiType": "chat"},
    "bluesminds": {"name": "BlueSminds",             "baseUrl": "https://api.bluesminds.com/v1",          "apiType": "chat"},
    # ── Embeddings ──
    "voyage":     {"name": "Voyage AI",              "baseUrl": "https://api.voyageai.com/v1",            "apiType": "embedding"},
    "jina":       {"name": "Jina AI",                "baseUrl": "https://api.jina.ai/v1",                 "apiType": "embedding"},
    # ── Image Generation ──
    "fal":        {"name": "FAL AI",                 "baseUrl": "https://rest.rifx.online/v1",            "apiType": "image"},
    "stability":  {"name": "Stability AI",           "baseUrl": "https://api.stability.ai/v1",            "apiType": "image"},
    "recraft":    {"name": "Recraft",                "baseUrl": "https://external.api.recraft.ai/v1",     "apiType": "image"},
    # ── TTS / STT ──
    "elevenlabs": {"name": "ElevenLabs",             "baseUrl": "https://api.elevenlabs.io/v1",           "apiType": "tts"},
    "deepgram":   {"name": "Deepgram",               "baseUrl": "https://api.deepgram.com/v1",            "apiType": "stt"},
    # ── Web Search ──
    "tavily":     {"name": "Tavily",                 "baseUrl": "https://api.tavily.com",                 "apiType": "websearch"},
    "brave":      {"name": "Brave Search",           "baseUrl": "https://api.search.brave.com",           "apiType": "websearch"},
    "serper":     {"name": "Serper",                 "baseUrl": "https://api.serper.dev",                 "apiType": "websearch"},
    "exa":        {"name": "Exa AI",                 "baseUrl": "https://api.exa.ai",                     "apiType": "websearch"},
}


# ─── DB HELPERS ───────────────────────────────────────────────────────

def get_conn(db_path):
    if not os.path.exists(db_path):
        sys.exit(f"[ERR] DB not found: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def load_active_nodes(conn):
    """Return provider nodes that have at least one active API key connection."""
    rows = conn.execute("""
        SELECT pn.id, pn.name, pn.type, pn.data,
               pc.authType, pc.data AS connData
        FROM providerNodes pn
        JOIN providerConnections pc ON pc.provider = pn.id
        WHERE pc.isActive = 1
          AND json_extract(pc.data, '$.apiKey') IS NOT NULL
          AND json_extract(pc.data, '$.apiKey') != ''
        ORDER BY pn.name
    """).fetchall()
    return rows


def load_all_nodes(conn):
    rows = conn.execute(
        "SELECT id, name, type, data FROM providerNodes ORDER BY name"
    ).fetchall()
    return rows


def node_to_dict(row):
    try:
        data = json.loads(row["data"]) if row["data"] else {}
    except json.JSONDecodeError:
        data = {}
    prefix = data.get("prefix", "?")
    baseUrl = data.get("baseUrl", "")
    apiType = data.get("apiType", "")
    return {
        "id": row["id"],
        "name": row["name"],
        "type": row["type"],
        "prefix": prefix,
        "baseUrl": baseUrl,
        "apiType": apiType,
    }


def conn_to_info(row):
    """Extract API key status from a providerConnection row."""
    try:
        cd = json.loads(row["connData"]) if row["connData"] else {}
    except json.JSONDecodeError:
        cd = {}
    api_key = cd.get("apiKey", "")
    test_status = cd.get("testStatus", "unknown")
    backoff = cd.get("backoffLevel", 0)
    last_error = cd.get("lastError", "")
    return {
        "has_key": bool(api_key),
        "test_status": test_status if api_key else "no_key",
        "backoff": backoff,
        "last_error": last_error[:60] if last_error else "",
        "key_preview": api_key[:8] + "..." + api_key[-4:] if api_key and len(api_key) > 16 else (api_key[:12] if api_key else ""),
    }


def group_nodes(nodes):
    groups = {}
    for n in nodes:
        groups.setdefault(n["prefix"], []).append(n)
    return groups


# ─── DISPLAY ──────────────────────────────────────────────────────────

def print_grouped(rows, json_out=False):
    """Print grouped view — only includes nodes with active API keys."""
    nodes = []
    for r in rows:
        nd = node_to_dict(r)
        ci = conn_to_info(r)
        nd["_conn"] = ci
        nodes.append(nd)

    groups = group_nodes(nodes)

    if json_out:
        out = {}
        for prefix in sorted(groups.keys()):
            out[prefix] = []
            for n in groups[prefix]:
                out[prefix].append({
                    "name": n["name"],
                    "baseUrl": n["baseUrl"],
                    "apiType": n["apiType"],
                    "apiKey": n["_conn"]["key_preview"],
                    "status": n["_conn"]["test_status"],
                    "backoff": n["_conn"]["backoff"],
                })
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    total_nodes = len(nodes)
    total_prefixes = len(groups)

    for prefix in sorted(groups.keys()):
        members = groups[prefix]
        n0 = members[0]
        reg = PROVIDER_REGISTRY.get(prefix)
        display_name = reg["name"] if reg else prefix
        print(f"\n{'🔹 ' if members[0]['_conn']['test_status'] == 'active' else '❌ '}"
              f"{prefix} ({display_name})  [{len(members)} key(s)]")
        print("─" * 60)
        for m in members:
            ci = m["_conn"]
            status_icon = "✅" if ci["test_status"] == "active" else ("⚠️" if ci["backoff"] > 0 else "❌")
            key_full = ci["key_preview"] or "(no key)"
            print(f"  {status_icon} {ci['test_status']:>8} | {key_full}")
            if ci["last_error"]:
                print(f"      err: {ci['last_error']}")
        print(f"      baseUrl: {m['baseUrl']}")
        print(f"      type:    {m['apiType']}")

    print(f"\n✅ Total: {total_nodes} API keys across {total_prefixes} providers (dengan key valid)")


def print_registry():
    """List ALL known providers (not just those in DB)."""
    print("\n📋 Semua Provider yg Didukung 9Router (Register)")
    print("=" * 60)
    by_type = {}
    for prefix, info in PROVIDER_REGISTRY.items():
        by_type.setdefault(info["apiType"], {})[prefix] = info

    for atype in sorted(by_type.keys()):
        print(f"\n  [{atype.upper()}]")
        for prefix in sorted(by_type[atype].keys()):
            info = by_type[atype][prefix]
            print(f"    {prefix:15s} — {info['name']:25s}  {info['baseUrl']}")
    print(f"\nTotal: {len(PROVIDER_REGISTRY)} provider prefixes")


# ─── ADD PROVIDER ─────────────────────────────────────────────────────

def add_provider(conn, prefix, api_key):
    """Add a new provider with API key to 9router DB.
    - Insert into providerNodes if prefix not already registered
    - Insert into providerConnections with the API key
    """
    reg = PROVIDER_REGISTRY.get(prefix)
    if not reg:
        # Allow custom prefix too (not just registry)
        print(f"[WARN] Unknown prefix '{prefix}'. Provide --baseurl if needed.")
        base_url = None
        name = prefix
        api_type = "chat"
    else:
        base_url = reg["baseUrl"]
        name = reg["name"]
        api_type = reg["apiType"]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    cur = conn.cursor()

    # Check if node already exists for this prefix
    existing = cur.execute(
        "SELECT id FROM providerNodes WHERE json_extract(data, '$.prefix') = ? LIMIT 1",
        (prefix,)
    ).fetchone()

    if existing:
        node_id = existing["id"]
        print(f"[INFO] Node '{prefix}' already exists (id: {node_id})")
    else:
        # Need baseUrl to create node
        if not base_url:
            print("[ERR] Unknown prefix and no --baseurl provided. Cannot create node.")
            return False
        node_id = f"openai-compatible-chat-{uuid.uuid4()}"
        node_data = json.dumps({
            "prefix": prefix,
            "baseUrl": base_url,
            "apiType": api_type,
        })
        cur.execute(
            "INSERT INTO providerNodes (id, type, name, data, createdAt, updatedAt) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (node_id, "openai-compatible", name, node_data, now, now)
        )
        print(f"[NEW] Node '{name}' (prefix: {prefix}) created → {node_id}")

    # Insert provider connection
    conn_id = str(uuid.uuid4())
    conn_data = json.dumps({
        "apiKey": api_key,
        "testStatus": "unknown",
        "backoffLevel": 0,
        "providerSpecificData": {
            "prefix": prefix,
            "apiType": api_type,
            "baseUrl": base_url or "",
            "nodeName": name,
            "connectionProxyEnabled": False,
            "connectionProxyUrl": "",
            "connectionNoProxy": "",
        },
    })
    cur.execute(
        "INSERT INTO providerConnections (id, provider, authType, name, priority, isActive, data, createdAt, updatedAt) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (conn_id, node_id, "apikey", f"Key 1", 1, 1, conn_data, now, now)
    )
    conn.commit()
    print(f"[ADD] API key added to '{prefix}' (conn: {conn_id})")
    print(f"[STATUS] Ready — 9router akan auto-test saat request pertama.")
    return True


# ─── MAIN ─────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="9router Provider Manager — group, list & add providers")
    ap.add_argument("--db", default=DEFAULT_DB, help="Path ke 9router SQLite DB")
    ap.add_argument("--json", action="store_true", help="Output JSON")
    ap.add_argument("--prefix", help="Filter prefix")
    ap.add_argument("--registry", action="store_true",
                    help="List semua provider yg didukung 9router (bukan cuma yg di DB)")
    ap.add_argument("--add", metavar="PREFIX",
                    help="Nambah provider (contoh: --add openai --apikey sk-...)")
    ap.add_argument("--apikey", metavar="KEY", help="API key provider")
    ap.add_argument("--baseurl", metavar="URL",
                    help="Base URL kustom (optional, buat prefix baru di luar registry)")
    args = ap.parse_args()

    # ── Registry only ──
    if args.registry:
        print_registry()
        return

    # ── Add provider ──
    if args.add:
        if not args.apikey:
            sys.exit("[ERR] --apikey wajib diisi saat --add")
        conn = get_conn(args.db)
        ok = add_provider(conn, args.add, args.apikey)
        conn.close()
        sys.exit(0 if ok else 1)

    # ── Default: group by prefix (hanya yg ada apikey valid) ──
    conn = get_conn(args.db)
    rows = load_active_nodes(conn)
    conn.close()

    # Filter by prefix
    if args.prefix:
        rows = [r for r in rows if json.loads(r["data"] if r["data"] else "{}").get("prefix") == args.prefix]
        if not rows:
            # Check if prefix exists but has no keys
            conn2 = get_conn(args.db)
            all_rows = load_all_nodes(conn2)
            conn2.close()
            exists = [r for r in all_rows if json.loads(r["data"] if r["data"] else "{}").get("prefix") == args.prefix]
            if exists:
                sys.exit(f"[INFO] Prefix '{args.prefix}' ada di DB tapi belum ada API key valid.\n"
                         f"       Tambah dgn: --add {args.prefix} --apikey YOUR_KEY")
            else:
                sys.exit(f"[ERR] Prefix '{args.prefix}' gak ditemukan. Cek --registry buat daftar.")

    print_grouped(rows, json_out=args.json)


if __name__ == "__main__":
    main()