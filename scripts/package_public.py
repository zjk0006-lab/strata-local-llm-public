"""Zip the public (sanitized) tree so it can be carried to a GitHub-ready machine.

Carrying a zip is safer than carrying a git repo: no accidental history, no
.git config with a real email, no stray ignored files.

Usage:
  python package_public.py --src "C:\\path\\strata-local-llm-public" \
      --out  "C:\\path\\strata-local-llm-public.zip"
"""
import argparse
import os
import zipfile

SKIP_DIRS = {"__pycache__", ".git"}
SKIP_EXT = {".pyc"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    src = os.path.abspath(src_root := a.src)
    if not os.path.isdir(src):
        raise SystemExit(f"not a directory: {src}")
    out = os.path.abspath(a.out)
    top = os.path.basename(src)

    n = 0
    total = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for dp, dns, fns in os.walk(src):
            dns[:] = [d for d in dns if d not in SKIP_DIRS]
            for fn in sorted(fns):
                if os.path.splitext(fn)[1].lower() in SKIP_EXT:
                    continue
                p = os.path.join(dp, fn)
                rel = os.path.relpath(p, src)
                z.write(p, os.path.join(top, rel))
                n += 1
                total += os.path.getsize(p)
    print(f"wrote {out}")
    print(f"  files={n}  raw={total/1024/1024:.2f} MB  zip={os.path.getsize(out)/1024/1024:.2f} MB")
    print("\n--- contents ---")
    with zipfile.ZipFile(out) as z:
        for i in z.infolist():
            print(f"  {i.file_size/1024:8.1f} KB  {i.filename}")


if __name__ == "__main__":
    main()
