"""Rewrite paths inside strata-<model>.json during a migration.

Approach: plain text replacement, NOT json.dump. Text replacement preserves the
original formatting/indentation; json.dump would reflow the whole file and make
diffing against the .bak painful.

Ordering rule: apply replacements from the MOST SPECIFIC prefix to the least
specific, otherwise a short prefix will clobber a longer one first.

After rewriting we MUST (a) json.load to prove validity and (b) os.path.exists
every path the engine reads - 11 of them on this deployment.

Usage:
  python rewrite_config.py --config "G:\\AI\\models\\...\\Strata\\strata-iq3_s.json" \
      --map "G:\\AI\\Strata=G:\\AI\\models\\Qwen3.8-Flash-Next-IQ3_S\\Strata" \
      --map "G:\\AI\\packs=G:\\AI\\models\\Qwen3.8-Flash-Next-IQ3_S\\packs" \
      [--no-backup]
"""
import argparse
import json
import os
import shutil
import sys


def collect_paths(cfg):
    """Yield every filesystem path the engine will try to open."""
    out = []
    for k in ("exe", "cwd", "tokenizer", "log"):
        if isinstance(cfg.get(k), str):
            out.append((k, cfg[k]))
    for p in cfg.get("lib_dirs", []):
        out.append(("lib_dirs", p))
    args = cfg.get("args", [])
    flag_flags = {"--pack", "--native", "--ple-gguf", "--expert-profile", "--mtp",
                  "--mmproj", "--tokenizer", "--lora"}
    for i, a in enumerate(args):
        if a in flag_flags and i + 1 < len(args):
            out.append((a, args[i + 1]))
    v = cfg.get("vision")
    if isinstance(v, dict):
        for k in ("exe", "mmproj", "model"):
            if isinstance(v.get(k), str):
                out.append(("vision." + k, v[k]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--map", action="append", default=[], help="OLD=NEW (repeatable)")
    ap.add_argument("--map-file", default="",
                    help="JSON file mapping OLD->NEW. PREFERRED on this box: Git Bash's "
                         "MSYS layer rewrites backslashes inside any argument containing "
                         "'=', so --map with Windows paths gets silently mangled when "
                         "passed from bash. A map-file avoids that entirely.")
    ap.add_argument("--no-backup", action="store_true")
    a = ap.parse_args()

    p = a.config
    raw = open(p, "r", encoding="utf-8").read()
    if not a.no_backup:
        shutil.copy2(p, p + ".bak")
        print(f"[bak] {p}.bak")

    pairs = []
    if a.map_file:
        for k, v in json.load(open(a.map_file, encoding="utf-8")).items():
            pairs.append((k, v))
    for m in a.map:
        if "=" not in m:
            sys.exit(f"bad --map (need OLD=NEW): {m}")
        old, new = m.split("=", 1)
        pairs.append((old, new))
    if not pairs:
        sys.exit("nothing to do: pass --map OLD=NEW or --map-file map.json")
    # most specific first
    pairs.sort(key=lambda t: len(t[0]), reverse=True)

    # JSON stores backslashes escaped ("G:\\AI\\..."), so a single-backslash --map
    # silently gets 0 hits. Try the escaped form too - this is a real trap.
    for old, new in pairs:
        n = raw.count(old)
        raw = raw.replace(old, new)
        n2 = 0
        e_old, e_new = old.replace("\\", "\\\\"), new.replace("\\", "\\\\")
        if e_old != old:
            n2 = raw.count(e_old)
            raw = raw.replace(e_old, e_new)
        print(f"[rep] {old}  ->  {new}   ({n} raw + {n2} escaped hits)")
        if n + n2 == 0:
            print("      [WARN] nothing matched - check the OLD prefix spelling")

    try:
        cfg = json.loads(raw)
    except Exception as e:
        sys.exit(f"[FAIL] JSON invalid after rewrite: {e}  (restore from .bak)")

    with open(p, "w", encoding="utf-8") as f:
        f.write(raw)
    print("[ok] JSON valid, written")

    print("--- path existence ---")
    bad = 0
    for tag, path in collect_paths(cfg):
        ok = os.path.exists(path)
        if not ok:
            bad += 1
        print(f"  {'OK ' if ok else 'MISS'} {tag:16s} {path}")
    print(f"total paths checked, missing = {bad}")
    sys.exit(0 if bad == 0 else 1)


if __name__ == "__main__":
    main()
