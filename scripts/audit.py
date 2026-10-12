"""Full consistency audit of a Strata deployment. Run after ANY change/migration.

Checks:
  1. junctions weights/packs/mtp exist, resolve, and are non-empty
  2. every path in strata-<model>.json exists (11 on this deployment)
  3. the three .cmd launchers are PURE ASCII + PURE CRLF (bare LF must be 0)
  4. the four shortcuts (Start Menu + Desktop x start/stop) resolve
  5. no stale references to old path prefixes anywhere in the tree

Usage:
  python audit.py --root "G:\\AI\\models\\Qwen3.8-Flash-Next-IQ3_S" \
      [--stale "G:\\AI\\Strata"] [--stale "G:\\AI\\_wheels"] [--stale "D:\\AI\\models\\Qwen"]
Exit 0 = clean, 1 = problems found.
"""
import argparse
import json
import os
import sys

import win32com.client

CMDS = ["start-strata.cmd", "stop-strata.cmd", "restart-strata.cmd"]
LINKS = ["weights", "packs", "mtp"]


def check_junctions(root):
    bad = 0
    for n in LINKS:
        p = os.path.join(root, n)
        if not os.path.isdir(p):
            print(f"  MISS  {n}: not a directory")
            bad += 1
            continue
        try:
            st = os.stat(p, follow_symlinks=False)
            reparse = bool(getattr(st, "st_reparse_tag", 0))
        except OSError:
            reparse = False
        cnt = len(os.listdir(p))
        flag = "OK " if (reparse and cnt) else "BAD"
        if flag == "BAD":
            bad += 1
        print(f"  {flag}  {n}: reparse={reparse} entries={cnt}")
    return bad


def check_config(cfg_path):
    try:
        cfg = json.load(open(cfg_path, encoding="utf-8"))
    except Exception as e:
        print(f"  BAD   config unreadable: {e}")
        return 1
    bad = 0
    items = [(k, cfg[k]) for k in ("exe", "cwd", "tokenizer", "log") if isinstance(cfg.get(k), str)]
    items += [("lib_dirs", p) for p in cfg.get("lib_dirs", [])]
    args = cfg.get("args", [])
    flags = {"--pack", "--native", "--ple-gguf", "--expert-profile", "--mtp", "--mmproj"}
    items += [(args[i], args[i + 1]) for i, x in enumerate(args) if x in flags and i + 1 < len(args)]
    v = cfg.get("vision")
    if isinstance(v, dict):
        items += [("vision." + k, v[k]) for k in ("exe", "mmproj", "model") if isinstance(v.get(k), str)]
    for tag, path in items:
        ok = os.path.exists(path)
        bad += 0 if ok else 1
        print(f"  {'OK ' if ok else 'MISS'} {tag:16s} {path}")
    print(f"  -> {len(items)} paths, missing {bad}")
    return bad


def check_cmds(root):
    bad = 0
    for fn in CMDS:
        p = os.path.join(root, fn)
        if not os.path.exists(p):
            print(f"  MISS  {fn}")
            bad += 1
            continue
        raw = open(p, "rb").read()
        bare_lf = raw.count(b"\n") - raw.count(b"\r\n")
        try:
            raw.decode("ascii")
            ascii_ok = True
        except UnicodeDecodeError:
            ascii_ok = False
        ok = bare_lf == 0 and ascii_ok
        bad += 0 if ok else 1
        print(f"  {'OK ' if ok else 'BAD'}  {fn}: {len(raw)} B  ascii={ascii_ok} bare_LF={bare_lf}")
    return bad


def check_shortcuts(prefix):
    sh = win32com.client.Dispatch("WScript.Shell")
    folders = {"startmenu": sh.SpecialFolders("Programs"), "desktop": sh.SpecialFolders("Desktop")}
    bad = 0
    for tag, folder in folders.items():
        for suffix in ("（启动）", "（停止）"):
            lnk = os.path.join(folder, f"{prefix}{suffix}.lnk")
            if not os.path.exists(lnk):
                print(f"  MISS  {tag}: {os.path.basename(lnk)}")
                bad += 1
                continue
            sc = sh.CreateShortCut(lnk)
            ok = os.path.exists(sc.TargetPath)
            bad += 0 if ok else 1
            print(f"  {'OK ' if ok else 'BAD'}  {tag}: {os.path.basename(lnk)} -> {sc.TargetPath}")
    return bad


def scan_stale(roots, stale):
    hits = []
    skipdirs = {".venv", "gitrepo", ".git", "__pycache__", "node_modules", "weights", "packs", "mtp", "engine"}
    exts = {".json", ".py", ".cmd", ".bat", ".md", ".txt", ".cfg", ".ini"}
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skipdirs]
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() not in exts:
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    if os.path.getsize(p) > 2_000_000:
                        continue
                    txt = open(p, encoding="utf-8", errors="ignore").read()
                except OSError:
                    continue
                for s in stale:
                    if s in txt:
                        hits.append((p, s))
    for p, s in hits:
        print(f"  STALE {p}  contains  {s}")
    print(f"  -> stale hits = {len(hits)}")
    return len(hits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--prefix", default="Strata 本地大模型")
    ap.add_argument("--stale", action="append", default=[])
    ap.add_argument("--scan-root", default=r"G:\AI")
    a = ap.parse_args()

    root = os.path.abspath(a.root)
    cfg = os.path.join(root, "Strata", "strata-iq3_s.json")

    total = 0
    print("=== 1. junctions ===")
    total += check_junctions(root)
    print("=== 2. config paths ===")
    total += check_config(cfg)
    print("=== 3. launcher encodings ===")
    total += check_cmds(root)
    print("=== 4. shortcuts ===")
    total += check_shortcuts(a.prefix)
    if a.stale:
        print("=== 5. stale path references ===")
        total += scan_stale([a.scan_root], a.stale)

    print(f"\nTOTAL PROBLEMS = {total}")
    sys.exit(0 if total == 0 else 1)


if __name__ == "__main__":
    main()
