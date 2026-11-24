#!/usr/bin/env python3
"""
9Router Provider Manager — Provider → Prefix → Model Inventory
=============================================================
Groups 9Router (and optional Nous Portal / Hermes) models into a clean
3-tier hierarchy:

    🏢 Provider  (e.g. Antigravity, Hcnsec, OpenCode)
       📁 Prefix  (e.g. ag, hcnsec, oc)
          • Model  (e.g. ag/gemini-3.8-flash, hcnsec/DeepSeek-V4-Flash)

Usage:
    python3 group_by_prefix.py                  # Default: 9router Provider → Prefix → Model
    python3 group_by_prefix.py --probe          # Real chat probe for every model
    python3 group_by_prefix.py --live-only      # Show only models answering LIVE (needs --probe)
    python3 group_by_prefix.py --prefix ag      # Filter by prefix substring
    python3 group_by_prefix.py --source portal  # Nous Portal models
    python3 group_by_prefix.py --source both    # 9router + Nous Portal
    python3 group_by_prefix.py --json           # Machine-readable JSON
    python3 group_by_prefix.py --registry       # List all 32+ supported providers in registry
    python3 group_by_prefix.py --add PREFIX --apikey KEY  # Add provider + key to 9router DB

Stdlib only.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DEFAULT_DB = Path(os.path.expanduser("~/.9router/db/data.sqlite"))
ROUTER_STATE = Path(os.path.expanduser("~/.9router/launcher.pid"))
ROUTER_KEY = Path(os.path.expanduser("~/.9router/api-key-hermes.full"))
DEFAULT_ROUTER_PORT = 20128
PORTAL_API = "https://inference-api.nousresearch.com/v1/models"
PORTAL_CACHE = Path(os.path.expanduser("~/.hermes/cache/portal_models_cache.json"))
PORTAL_TTL = 3600  # seconds

# ─── PROVIDER REGISTRY ────────────────────────────────────────────────
PROVIDER_REGISTRY = {
    # ── Chat/LLM ──
    "ag":          {"name": "Antigravity",            "baseUrl": "",                                                      "apiType": "oauth"},
    "antigravity": {"name": "Antigravity",            "baseUrl": "",                                                      "apiType": "oauth"},
    "hcnsec":      {"name": "GLM Coding (HCN)",       "baseUrl": "https://api.hcnsec.cn/v1",                              "apiType": "chat"},
    "oc":          {"name": "OpenCode Zen",           "baseUrl": "https://opencode.ai/zen/v1",                             "apiType": "chat"},
    "kimi":        {"name": "Kimi (Moonshot)",        "baseUrl": "https://api.moonshot.cn/v1",                            "apiType": "chat"},
    "minimax":     {"name": "MiniMax",                "baseUrl": "https://api.minimax.chat/v1",                           "apiType": "chat"},
    "openai":      {"name": "OpenAI",                 "baseUrl": "https://api.openai.com/v1",                             "apiType": "chat"},
    "deepseek":    {"name": "DeepSeek",               "baseUrl": "https://api.deepseek.com/v1",                            "apiType": "chat"},
    "groq":        {"name": "Groq",                   "baseUrl": "https://api.groq.com/openai/v1",                        "apiType": "chat"},
    "xai":         {"name": "xAI Grok",               "baseUrl": "https://api.x.ai/v1",                                   "apiType": "chat"},
    "gcli":        {"name": "xAI Grok CLI",           "baseUrl": "",                                                      "apiType": "oauth"},
    "grok-cli":    {"name": "xAI Grok CLI",           "baseUrl": "",                                                      "apiType": "oauth"},
    "mistral":     {"name": "Mistral",                "baseUrl": "https://api.mistral.ai/v1",                              "apiType": "chat"},
    "qwen":        {"name": "Qwen (DashScope)",       "baseUrl": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1", "apiType": "chat"},
    "openrouter":  {"name": "OpenRouter",             "baseUrl": "https://openrouter.ai/api/v1",                           "apiType": "chat"},
    "nvidia":      {"name": "NVIDIA NIM",             "baseUrl": "https://integrate.api.nvidia.com/v1",                    "apiType": "chat"},
    "gemini":      {"name": "Google Gemini",          "baseUrl": "https://generativelanguage.googleapis.com/v1beta/openai/", "apiType": "chat"},
    "together":    {"name": "Together AI",            "baseUrl": "https://api.together.xyz/v1",                            "apiType": "chat"},
    "fireworks":   {"name": "Fireworks AI",           "baseUrl": "https://api.fireworks.ai/inference/v1",                  "apiType": "chat"},
    "cohere":      {"name": "Cohere",                 "baseUrl": "https://api.cohere.com/v1",                              "apiType": "chat"},
    "anthropic":   {"name": "Anthropic",              "baseUrl": "https://api.anthropic.com/v1",                           "apiType": "chat"},
    "iflow":       {"name": "iFlow",                  "baseUrl": "https://inference.iflow.ai/v1",                          "apiType": "chat"},
    "perplexity":  {"name": "Perplexity",             "baseUrl": "https://api.perplexity.ai",                              "apiType": "chat"},
    "kiro":        {"name": "Kiro AI",                "baseUrl": "https://runtime.us-east-1.kiro.dev",                     "apiType": "oauth"},
    "kr":          {"name": "Kiro AI",                "baseUrl": "https://runtime.us-east-1.kiro.dev",                     "apiType": "oauth"},
    "bluesminds":  {"name": "BlueSminds",             "baseUrl": "https://api.bluesminds.com/v1",                          "apiType": "chat"},
    "stepmini":    {"name": "StepFun Mini",           "baseUrl": "https://api.stepfun.ai/step_plan/v1",                    "apiType": "chat"},
    "respan":      {"name": "Respan",                 "baseUrl": "https://api.respan.ai/api/v1",                           "apiType": "chat"},
    "numes":       {"name": "Numes",                  "baseUrl": "https://api.numes.ai/api/v1",                            "apiType": "chat"},
    "cfproxy":     {"name": "Cloudflare Workers AI",  "baseUrl": "http://127.0.0.1:8750/v1",                              "apiType": "chat"},
    "mmf":         {"name": "MMFlow",                 "baseUrl": "",                                                      "apiType": "chat"},
    # ── Embeddings ──
    "voyage":      {"name": "Voyage AI",              "baseUrl": "https://api.voyageai.com/v1",                            "apiType": "embedding"},
    "jina":        {"name": "Jina AI",                "baseUrl": "https://api.jina.ai/v1",                                 "apiType": "embedding"},
    # ── Image ──
    "fal":         {"name": "FAL AI",                 "baseUrl": "https://rest.rifx.online/v1",                            "apiType": "image"},
    "stability":   {"name": "Stability AI",           "baseUrl": "https://api.stability.ai/v1",                            "apiType": "image"},
    "recraft":     {"name": "Recraft",                "baseUrl": "https://external.api.recraft.ai/v1",                     "apiType": "image"},
    # ── TTS / STT ──
    "elevenlabs":  {"name": "ElevenLabs",             "baseUrl": "https://api.elevenlabs.io/v1",                           "apiType": "tts"},
    "deepgram":    {"name": "Deepgram",               "baseUrl": "https://api.deepgram.com/v1",                            "apiType": "stt"},
    # ── Web Search ──
    "tavily":      {"name": "Tavily",                 "baseUrl": "https://api.tavily.com",                                 "apiType": "search"},
    "brave":       {"name": "Brave Search",           "baseUrl": "https://api.search.brave.com",                          "apiType": "search"},
    "serper":      {"name": "Serper",                 "baseUrl": "https://api.serper.dev",                                 "apiType": "search"},
    "exa":         {"name": "Exa AI",                 "baseUrl": "https://api.exa.ai",                                     "apiType": "search"},
}

PREFIX_NORMALIZE = {
    "antigravity": "ag",
    "grok-cli": "gcli",
    "kiro": "kr",
}

STATE_ICON = {
    "LIVE": "🟢",
    "RATE": "🟡",
    "AUTH": "🔴",
    "BILLING": "💳",
    "DOWN": "🔴",
    "EMPTY": "⚪",
}


# --------------------------------------------------------------------------- #
# Database Helpers
# --------------------------------------------------------------------------- #
def get_db(path: Path) -> sqlite3.Connection:
    if not path.exists():
        sys.exit(f"[ERR] DB not found: {path}")
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def get_nodes(con: sqlite3.Connection) -> dict:
    nodes = {}
    for r in con.execute("SELECT id, name, type, data FROM providerNodes ORDER BY name"):
        try:
            d = json.loads(r["data"] or "{}")
        except Exception:
            d = {}
        nodes[r["id"]] = {
            "id": r["id"],
            "name": r["name"],
            "type": r["type"],
            "prefix": d.get("prefix") or "",
            "baseUrl": d.get("baseUrl") or "",
            "apiType": d.get("apiType") or "chat",
        }
    return nodes


def get_connections(con: sqlite3.Connection, nodes: dict) -> list:
    conns = []
    for r in con.execute(
        "SELECT id, provider, authType, name, priority, isActive, data FROM providerConnections"
    ):
        try:
            d = json.loads(r["data"] or "{}")
        except Exception:
            d = {}
        psd = d.get("providerSpecificData") or {}
        raw_pfx = psd.get("prefix") or nodes.get(r["provider"], {}).get("prefix") or r["provider"]
        pfx = PREFIX_NORMALIZE.get(raw_pfx, raw_pfx)
        conns.append({
            "id": r["id"],
            "provider": r["provider"],
            "authType": r["authType"],
            "name": r["name"],
            "priority": r["priority"],
            "isActive": bool(r["isActive"]),
            "testStatus": d.get("testStatus") or "unknown",
            "errorCode": d.get("errorCode"),
            "prefix": pfx,
            "baseUrl": psd.get("baseUrl") or nodes.get(r["provider"], {}).get("baseUrl") or "",
            "nodeName": nodes.get(r["provider"], {}).get("name") or PROVIDER_REGISTRY.get(pfx, {}).get("name") or pfx,
            "apiKey": d.get("apiKey") or "",
            "accessToken": d.get("accessToken") or "",
            "enabledModels": psd.get("enabledModels") or [],
        })
    return conns


def get_kv(con: sqlite3.Connection) -> tuple[dict, dict]:
    custom, disabled = {}, {}
    for r in con.execute(
        "SELECT scope, key, value FROM kv WHERE scope IN ('customModels', 'disabledModels')"
    ):
        if r["scope"] == "customModels":
            parts = r["key"].split("|")
            node_id_or_pfx = parts[0] if parts else ""
            try:
                v = json.loads(r["value"])
                custom.setdefault(node_id_or_pfx, []).append(
                    v.get("id") or (parts[1] if len(parts) > 1 else "")
                )
            except Exception:
                pass
        else:
            try:
                arr = json.loads(r["value"])
                disabled[r["key"]] = arr if isinstance(arr, list) else []
            except Exception:
                pass
    return custom, disabled


# --------------------------------------------------------------------------- #
# Live Router Models & Probing
# --------------------------------------------------------------------------- #
def detect_router_port() -> int:
    try:
        d = json.loads(ROUTER_STATE.read_text())
        p = int(d.get("port") or 0)
        if p > 0:
            return p
    except Exception:
        pass
    return DEFAULT_ROUTER_PORT


def fetch_live_models(port: int | None = None) -> list:
    port = port or detect_router_port()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/models",
                                 headers={"Accept": "application/json"})
    if ROUTER_KEY.exists():
        tok = ROUTER_KEY.read_text().strip()
        if tok:
            req.add_header("Authorization", f"Bearer {tok}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode()
        obj, _ = json.JSONDecoder().raw_decode(raw.strip())
        return obj.get("data", []) if isinstance(obj, dict) else []
    except Exception as e:
        sys.stderr.write(f"[WARN] Failed to fetch live models from router: {e}\n")
        return []


def probe_live(model_ids: list[str], workers: int = 8, timeout: int = 25, port: int | None = None) -> dict:
    port = port or detect_router_port()
    url = f"http://127.0.0.1:{port}/v1/chat/completions"
    ids = list(dict.fromkeys(i for i in model_ids if i))

    def probe_one(mid: str):
        payload = json.dumps({
            "model": mid,
            "messages": [{"role": "user", "content": "PONG"}],
            "max_tokens": 16,
            "stream": False,
        }).encode()
        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read(8192).decode("utf-8", "replace")
                lat = int((time.time() - t0) * 1000)
                return mid, ("LIVE" if '"choices"' in raw else "EMPTY"), lat, ""
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read(512).decode("utf-8", "replace")
            except Exception:
                pass
            low = body.lower()
            if e.code == 429:
                state = "RATE"
            elif e.code in (401, 403):
                state = "AUTH"
            elif e.code == 402 or "insufficient" in low or "credit" in low:
                state = "BILLING"
            else:
                state = "DOWN"
            return mid, state, 0, body[:140]
        except Exception as e:
            return mid, "DOWN", 0, f"{type(e).__name__}: {e}"[:140]

    out = {}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        for mid, state, lat, detail in ex.map(probe_one, ids):
            out[mid] = {"state": state, "latency": lat, "detail": detail}
    return out


# --------------------------------------------------------------------------- #
# Nous Portal & Hermes Catalogs
# --------------------------------------------------------------------------- #
def _portal_token() -> str:
    auth = Path(os.path.expanduser("~/.hermes/auth.json"))
    if not auth.exists():
        sys.exit("[ERR] auth.json not found — run `hermes portal login` first")
    d = json.loads(auth.read_text())
    tok = (d.get("providers", {}).get("nous", {}) or {}).get("access_token", "")
    if not tok:
        sys.exit("[ERR] Nous Portal access_token missing — run `hermes portal login`")
    return tok


def fetch_portal_models(refresh: bool = False) -> list:
    if not refresh and PORTAL_CACHE.exists():
        age = time.time() - PORTAL_CACHE.stat().st_mtime
        if age < PORTAL_TTL:
            try:
                return json.loads(PORTAL_CACHE.read_text())
            except Exception:
                pass
    req = urllib.request.Request(
        PORTAL_API, headers={"Authorization": f"Bearer {_portal_token()}",
                             "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    PORTAL_CACHE.parent.mkdir(parents=True, exist_ok=True)
    PORTAL_CACHE.write_text(json.dumps(data))
    return data


# --------------------------------------------------------------------------- #
# Core Builder: Provider → Prefix → Model
# --------------------------------------------------------------------------- #
def build_tree(source: str = "9router", db_path: Path = DEFAULT_DB, no_live: bool = False,
               refresh_portal: bool = False, free_only: bool = False) -> dict:
    """Builds canonical Provider → Prefix → Model hierarchy."""
    tree = {}

    def get_or_create_provider(name: str, base_url: str = "", source_type: str = "9router") -> dict:
        if name not in tree:
            tree[name] = {
                "name": name,
                "baseUrl": base_url,
                "source": source_type,
                "conns": [],
                "prefixes": {},
            }
        elif base_url and not tree[name]["baseUrl"]:
            tree[name]["baseUrl"] = base_url
        return tree[name]

    # 1. 9Router source
    if source in ("9router", "both", "all") and db_path.exists():
        con = get_db(db_path)
        nodes = get_nodes(con)
        conns = get_connections(con, nodes)
        custom, disabled = get_kv(con)
        con.close()

        # Seed from providerNodes
        for nid, n in nodes.items():
            pfx = n["prefix"] or nid
            pfx = PREFIX_NORMALIZE.get(pfx, pfx)
            prov_name = n["name"] or PROVIDER_REGISTRY.get(pfx, {}).get("name") or pfx
            prov = get_or_create_provider(prov_name, n["baseUrl"], "9router")
            p_entry = prov["prefixes"].setdefault(pfx, {"prefix": pfx, "models": {}})
            
            for mid in custom.get(nid, []):
                full_id = f"{pfx}/{mid}" if "/" not in mid else mid
                p_entry["models"][full_id] = {
                    "id": full_id, "bare": mid, "context_length": None, "vision": False, "source": "kv"
                }

        # Seed from connections (covers OAuth built-ins without node)
        for c in conns:
            pfx = c["prefix"]
            prov_name = c["nodeName"] or PROVIDER_REGISTRY.get(pfx, {}).get("name") or pfx
            prov = get_or_create_provider(prov_name, c["baseUrl"], "9router")
            prov["conns"].append(c)
            p_entry = prov["prefixes"].setdefault(pfx, {"prefix": pfx, "models": {}})
            
            for mid in c.get("enabledModels") or []:
                full_id = f"{pfx}/{mid}" if "/" not in mid else mid
                p_entry["models"][full_id] = {
                    "id": full_id, "bare": mid, "context_length": None, "vision": False, "source": "conn"
                }

        # Merge live router catalog (/v1/models)
        if not no_live:
            live = fetch_live_models()
            for m in live:
                mid = m.get("id") or ""
                if "/" not in mid:
                    continue
                pfx, bare = mid.split("/", 1)
                pfx = PREFIX_NORMALIZE.get(pfx, pfx)
                
                prov_name = None
                for n in nodes.values():
                    if PREFIX_NORMALIZE.get(n["prefix"], n["prefix"]) == pfx:
                        prov_name = n["name"]
                        break
                if not prov_name:
                    prov_name = PROVIDER_REGISTRY.get(pfx, {}).get("name") or pfx.capitalize()

                prov = get_or_create_provider(prov_name, "", "9router")
                p_entry = prov["prefixes"].setdefault(pfx, {"prefix": pfx, "models": {}})
                
                caps = m.get("capabilities") if isinstance(m.get("capabilities"), dict) else {}
                ctx = m.get("context_length") or caps.get("context_window")
                vis = bool(m.get("vision") or caps.get("vision"))
                
                cur = p_entry["models"].get(mid)
                if cur:
                    cur.update({"context_length": ctx, "vision": vis, "source": "live"})
                else:
                    p_entry["models"][mid] = {
                        "id": mid, "bare": bare, "context_length": ctx, "vision": vis, "source": "live"
                    }

    # 2. Nous Portal source
    if source in ("portal", "both", "all"):
        portal_data = fetch_portal_models(refresh=refresh_portal)
        prov = get_or_create_provider("Nous Portal", "https://inference-api.nousresearch.com/v1", "portal")
        
        for m in portal_data:
            mid = m.get("id") or ""
            if "/" not in mid:
                pfx, bare = "(direct)", mid
            else:
                pfx, bare = mid.split("/", 1)
                
            p = m.get("pricing") or {}
            is_free = (float(p.get("prompt", 1) or 0) == 0 and float(p.get("completion", 1) or 0) == 0)
            if free_only and not is_free:
                continue

            p_entry = prov["prefixes"].setdefault(pfx, {"prefix": pfx, "models": {}})
            p_entry["models"][mid] = {
                "id": mid,
                "bare": bare,
                "context_length": m.get("context_length"),
                "free": is_free,
                "reasoning": bool(m.get("reasoning")),
                "source": "portal",
            }

    # 3. Hermes config source
    if source in ("hermes", "all"):
        try:
            import yaml
            cfg_p = Path(os.path.expanduser("~/.hermes/config.yaml"))
            if cfg_p.exists():
                cfg = yaml.safe_load(cfg_p.read_text()) or {}
                for cp in cfg.get("custom_providers", []):
                    group = cp.get("provider_group") or "Hermes Custom"
                    name = cp.get("name") or ""
                    prov = get_or_create_provider(group, cp.get("base_url") or "", "hermes")
                    p_entry = prov["prefixes"].setdefault(name, {"prefix": name, "models": {}})
                    for m_key, m_val in (cp.get("models") or {}).items():
                        m_id = m_key if "/" in m_key else f"{name}/{m_key}"
                        ctx = m_val.get("context_length") if isinstance(m_val, dict) else None
                        p_entry["models"][m_id] = {
                            "id": m_id, "bare": m_key, "context_length": ctx, "vision": False, "source": "hermes"
                        }
        except Exception:
            pass

    return tree


# --------------------------------------------------------------------------- #
# Output Formatters
# --------------------------------------------------------------------------- #
def render_text(tree: dict, filter_sub: str | None = None, live_mode: bool = False) -> str:
    lines = []
    now_str = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    total_provs = 0
    total_prefixes = 0
    total_models = 0

    filtered_tree = {}
    for prov_name, prov in sorted(tree.items()):
        matched_prefixes = {}
        for pfx, pdata in sorted(prov["prefixes"].items()):
            if filter_sub and filter_sub.lower() not in pfx.lower() and filter_sub.lower() not in prov_name.lower():
                continue
            models = sorted(pdata["models"].values(), key=lambda x: x["id"])
            if models:
                matched_prefixes[pfx] = models
                total_models += len(models)
                total_prefixes += 1
        if matched_prefixes:
            filtered_tree[prov_name] = (prov, matched_prefixes)
            total_provs += 1

    lines.append(f"# Model Inventory (Provider → Prefix → Model)  ({now_str})")
    lines.append(f"{total_provs} providers · {total_prefixes} prefixes · {total_models} models\n")

    for prov_name, (prov, prefixes) in sorted(filtered_tree.items()):
        conns = prov.get("conns", [])
        active_keys = sum(1 for c in conns if c["isActive"])
        total_keys = len(conns)
        
        if total_keys > 0:
            key_tag = f"Keys: {active_keys}/{total_keys} active"
        elif prov.get("source") == "portal":
            key_tag = "Catalog: Nous Portal"
        elif prov.get("source") == "hermes":
            key_tag = "Config: custom_providers"
        else:
            key_tag = "Keys: live catalog"

        base_tag = f"BaseURL: {prov['baseUrl']}" if prov.get("baseUrl") else "BaseURL: -"

        lines.append("━" * 68)
        lines.append(f"🏢 Provider: {prov_name}")
        lines.append(f"   {key_tag} · {base_tag}")
        lines.append("─" * 68)

        for pfx, models in prefixes.items():
            lines.append(f"  📁 Prefix: {pfx} ({len(models)} models)")
            for m in models:
                parts = []
                st = m.get("state")
                if st:
                    parts.append(STATE_ICON.get(st, "?"))
                    if m.get("latency"):
                        parts.append(f"[{m['latency']}ms]")
                    if st in ("AUTH", "BILLING", "DOWN", "EMPTY", "RATE") and m.get("detail"):
                        parts.append(f"({m['detail'][:60]})")
                
                if m.get("free"):
                    parts.append("[FREE]")
                if m.get("vision"):
                    parts.append("[Vision]")
                ctx = m.get("context_length")
                if isinstance(ctx, int):
                    parts.append(f"[ctx: {ctx:,}]")

                meta_str = " ".join(parts)
                lines.append(f"     • {m['id']: <40} {meta_str}")
        lines.append("")

    return "\n".join(lines).strip()


def render_json(tree: dict, filter_sub: str | None = None) -> str:
    out = {
        "hierarchy": "provider_prefix_model",
        "timestamp": _dt.datetime.now().isoformat(),
        "providers": []
    }
    total_provs = 0
    total_pfx = 0
    total_mods = 0

    for prov_name, prov in sorted(tree.items()):
        prov_entry = {
            "name": prov_name,
            "baseUrl": prov.get("baseUrl") or "",
            "source": prov.get("source"),
            "keysTotal": len(prov.get("conns", [])),
            "keysActive": sum(1 for c in prov.get("conns", []) if c["isActive"]),
            "prefixes": []
        }
        for pfx, pdata in sorted(prov["prefixes"].items()):
            if filter_sub and filter_sub.lower() not in pfx.lower() and filter_sub.lower() not in prov_name.lower():
                continue
            models = sorted(pdata["models"].values(), key=lambda x: x["id"])
            if models:
                prov_entry["prefixes"].append({
                    "prefix": pfx,
                    "totalModels": len(models),
                    "models": models
                })
                total_mods += len(models)
                total_pfx += 1
        if prov_entry["prefixes"]:
            out["providers"].append(prov_entry)
            total_provs += 1

    out["totalProviders"] = total_provs
    out["totalPrefixes"] = total_pfx
    out["totalModels"] = total_mods
    return json.dumps(out, indent=2)


# --------------------------------------------------------------------------- #
# Provider Registry & DB Write Helpers
# --------------------------------------------------------------------------- #
def print_registry():
    print("📋 Semua Provider yg Didukung 9Router (Register)")
    print("=" * 60)
    cats = {"chat": "CHAT", "oauth": "CHAT (OAUTH)", "embedding": "EMBEDDING",
            "image": "IMAGE", "tts": "TTS", "stt": "STT", "search": "WEBSEARCH"}
    by_cat = {}
    for pfx, info in PROVIDER_REGISTRY.items():
        by_cat.setdefault(info.get("apiType", "chat"), []).append((pfx, info))

    for cat_key, cat_name in cats.items():
        items = by_cat.get(cat_key, [])
        if not items:
            continue
        print(f"\n  [{cat_name}]")
        for pfx, info in sorted(items):
            url = info.get("baseUrl") or "(builtin / oauth)"
            print(f"    {pfx: <15} — {info['name']: <26} {url}")

    print(f"\nTotal: {len(PROVIDER_REGISTRY)} provider prefixes")


def add_provider(db_path: Path, prefix: str, api_key: str, base_url: str | None = None) -> bool:
    reg = PROVIDER_REGISTRY.get(prefix)
    if not reg:
        if not base_url:
            sys.exit(f"[ERR] Prefix '{prefix}' tidak ada di registry. Berikan --baseurl URL.")
        name = prefix.capitalize()
        api_type = "chat"
    else:
        name = reg["name"]
        api_type = reg["apiType"]
        base_url = base_url or reg["baseUrl"]

    if not db_path.exists():
        sys.exit(f"[ERR] DB not found at: {db_path}")

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    # Check node
    existing = cur.execute(
        "SELECT id FROM providerNodes WHERE json_extract(data, '$.prefix') = ? LIMIT 1",
        (prefix,)
    ).fetchone()

    if existing:
        node_id = existing["id"]
        print(f"[INFO] Node '{prefix}' already exists (id: {node_id})")
    else:
        node_id = f"openai-compatible-chat-{uuid.uuid4()}"
        node_data = json.dumps({"prefix": prefix, "baseUrl": base_url, "apiType": api_type})
        cur.execute(
            "INSERT INTO providerNodes (id, type, name, data, createdAt, updatedAt) VALUES (?, ?, ?, ?, ?, ?)",
            (node_id, "openai-compatible", name, node_data, now, now)
        )
        print(f"[NEW] Node '{name}' (prefix: {prefix}) created → {node_id}")

    # Add connection
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
        }
    })
    cur.execute(
        "INSERT INTO providerConnections (id, provider, authType, name, priority, isActive, data, createdAt, updatedAt) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (conn_id, node_id, "apikey", "Key 1", 1, 1, conn_data, now, now)
    )
    con.commit()
    con.close()
    print(f"[ADD] API key added to '{prefix}' (conn: {conn_id})")
    print(f"[STATUS] Ready — 9router akan auto-test saat request pertama.")
    return True


# --------------------------------------------------------------------------- #
# CLI Entrypoint
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="9Router Provider Manager — Provider → Prefix → Model")
    ap.add_argument("--source", choices=["9router", "portal", "hermes", "both", "all"], default="9router",
                    help="Sumber model (default: 9router)")
    ap.add_argument("--prefix", "--filter", dest="prefix", help="Filter nama provider atau prefix substring")
    ap.add_argument("--json", action="store_true", help="Output format JSON")
    ap.add_argument("--db", default=DEFAULT_DB, type=Path, help="Path ke 9router data.sqlite")
    ap.add_argument("--registry", action="store_true", help="List semua provider yg didukung di registry")
    ap.add_argument("--add", metavar="PREFIX", help="Tambah provider baru ke DB")
    ap.add_argument("--apikey", metavar="KEY", help="API key untuk --add")
    ap.add_argument("--baseurl", metavar="URL", help="Base URL kustom untuk --add")
    ap.add_argument("--probe", action="store_true", help="Real chat-probe ke setiap model via router")
    ap.add_argument("--live-only", action="store_true", help="Hanya tampilkan model yg menjawab LIVE")
    ap.add_argument("--workers", type=int, default=8, help="Worker concurrency untuk --probe")
    ap.add_argument("--no-live", action="store_true", help="Lewati merge catalog router live /v1/models")
    ap.add_argument("--refresh", action="store_true", help="Refresh cache Nous Portal")
    ap.add_argument("--free", action="store_true", help="(Portal) Hanya tampilkan model free")
    args = ap.parse_args()

    # 1. Registry list
    if args.registry:
        print_registry()
        return

    # 2. Add provider
    if args.add:
        if not args.apikey:
            sys.exit("[ERR] --apikey wajib diisi saat menggunakan --add")
        ok = add_provider(args.db, args.add, args.apikey, args.baseurl)
        sys.exit(0 if ok else 1)

    # 3. Build Provider → Prefix → Model tree
    tree = build_tree(
        source=args.source,
        db_path=args.db,
        no_live=args.no_live,
        refresh_portal=args.refresh,
        free_only=args.free,
    )

    # 4. Probe live if requested
    if args.probe or args.live_only:
        all_ids = []
        for prov in tree.values():
            for pdata in prov["prefixes"].values():
                all_ids.extend(pdata["models"].keys())
        probes = probe_live(all_ids, workers=args.workers)
        
        # Attach probe results
        for prov in tree.values():
            for pdata in prov["prefixes"].values():
                for mid, m in list(pdata["models"].items()):
                    if mid in probes:
                        m.update(probes[mid])
                    if args.live_only and m.get("state") != "LIVE":
                        del pdata["models"][mid]

    # 5. Output
    if args.json:
        print(render_json(tree, filter_sub=args.prefix))
    else:
        print(render_text(tree, filter_sub=args.prefix, live_mode=args.probe))


if __name__ == "__main__":
    main()
