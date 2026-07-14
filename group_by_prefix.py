#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
9router Prefix Grouper
======================
Group all 9router provider/model nodes by their `prefix` (e.g. hcnsec/*,
nous/*, oc/*). Reads the live 9router SQLite DB and prints a clean grouped
view — useful for auditing which prefixes exist and which provider each maps to.

Usage:
    python3 group_by_prefix.py                 # table view
    python3 group_by_prefix.py --json          # JSON output
    python3 group_by_prefix.py --prefix hcnsec # filter one prefix
    python3 group_by_prefix.py --db /path/to/data.sqlite

The DB path defaults to ~/.9router/db/data.sqlite
"""
import argparse
import json
import os
import sqlite3
import sys

DEFAULT_DB = os.path.expanduser("~/.9router/db/data.sqlite")


def load_nodes(db_path):
    """Return list of dicts: {id, name, type, prefix, baseUrl, apiType}."""
    if not os.path.exists(db_path):
        sys.exit(f"[ERR] DB not found: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, name, type, data FROM providerNodes ORDER BY name"
    ).fetchall()
    conn.close()

    nodes = []
    for r in rows:
        try:
            data = json.loads(r["data"]) if r["data"] else {}
        except json.JSONDecodeError:
            data = {}
        nodes.append({
            "id": r["id"],
            "name": r["name"],
            "type": r["type"],
            "prefix": data.get("prefix", "?"),
            "baseUrl": data.get("baseUrl", ""),
            "apiType": data.get("apiType", ""),
        })
    return nodes


def group_by_prefix(nodes):
    groups = {}
    for n in nodes:
        groups.setdefault(n["prefix"], []).append(n)
    return groups


def print_table(groups):
    for prefix in sorted(groups.keys()):
        members = groups[prefix]
        print(f"\n🔹 Prefix: {prefix}  ({len(members)} node)")
        print("─" * 60)
        for m in members:
            print(f"  • {m['name']:<14} [{m['type']}]")
            if m["baseUrl"]:
                print(f"      baseUrl : {m['baseUrl']}")
            if m["apiType"]:
                print(f"      apiType : {m['apiType']}")
    print(f"\n✅ Total: {sum(len(v) for v in groups.values())} nodes, "
          f"{len(groups)} prefixes")


def main():
    ap = argparse.ArgumentParser(description="Group 9router models by prefix")
    ap.add_argument("--db", default=DEFAULT_DB, help="Path to 9router SQLite DB")
    ap.add_argument("--json", action="store_true", help="Output as JSON")
    ap.add_argument("--prefix", help="Only show this prefix")
    args = ap.parse_args()

    nodes = load_nodes(args.db)
    groups = group_by_prefix(nodes)

    if args.prefix:
        groups = {k: v for k, v in groups.items() if k == args.prefix}
        if not groups:
            sys.exit(f"[ERR] prefix '{args.prefix}' not found")

    if args.json:
        print(json.dumps(groups, indent=2, ensure_ascii=False))
    else:
        print_table(groups)


if __name__ == "__main__":
    main()
