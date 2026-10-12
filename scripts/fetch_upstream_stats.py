"""Fetch upstream Strata repo stats so the README can cite real numbers.

Run this on a machine with GitHub access, then paste the printed line into
README.md where the placeholder is marked. Never invent a star count.

Usage:
  python fetch_upstream_stats.py            # prints a ready-to-paste markdown line
  python fetch_upstream_stats.py --json     # raw fields
"""
import argparse
import json
import urllib.request

REPO = "Niko1221/Strata"


def fetch():
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}",
        headers={"User-Agent": "strata-notes-stats", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    d = fetch()
    stars = d.get("stargazers_count")
    forks = d.get("forks_count")
    lic = (d.get("license") or {}).get("spdx_id")
    desc = d.get("description") or ""
    pushed = (d.get("pushed_at") or "")[:10]
    if a.json:
        print(json.dumps(d, ensure_ascii=False, indent=1)[:2000])
        return
    print(f"stars={stars} forks={forks} license={lic} pushed={pushed}")
    print(f"description: {desc}")
    print("\n--- paste into README.md (replacing the STAR_PLACEHOLDER line) ---")
    print(f"**上游 Strata：⭐ {stars} · {forks} forks · {lic} · 最后更新 {pushed}**")


if __name__ == "__main__":
    main()
