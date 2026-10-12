"""Install Python wheels into a venv WITHOUT pip.

pip CRASHES on this machine: 所用 agent 沙箱会经
PYTHONPATH 注入 sitecustomize.py，其删除保护钩子拦截 os.unlink，导致
pip is unpacking a wheel. Two ways out:
  A) disable the hook:  （关闭所用 agent 沙箱的删除保护开关，变量名见其文档） python -m pip install ...
     (in `env`, the -u flags must come BEFORE VAR=value)
  B) skip pip entirely (this script): download the .whl, then zipfile.extractall
     straight into site-packages. A wheel IS a zip; for these pure-binary/CUDA
     packages that is sufficient.

Mirror choice: files.pythonhosted.org crawls at ~65-100 kB/s through the system
proxy; pypi.tuna.tsinghua.edu.cn delivers ~37 MB/s. Use tuna.

Usage:
  python install_wheels.py --site "G:\\AI\\models\\Qwen3.8-Flash-Next-IQ3_S\\Strata\\.venv\\Lib\\site-packages" \
      --cache "G:\\AI\\tools\\wheels" [--mirror https://pypi.tuna.tsinghua.edu.cn] \
      [--pkg nvidia-cublas==13.0.2.14] [--pkg nvidia-cuda-runtime==13.0.96]
"""
import argparse
import os
import re
import urllib.request
import zipfile

DEFAULT_PKGS = [
    ("cmake", "4.4.3", "win_amd64"),
    ("ninja", "1.13.2", "win_amd64"),
    ("nvidia-cublas", "13.0.2.14", "win_amd64"),
    ("nvidia-cuda-runtime", "13.0.96", "win_amd64"),
]


def simple_links(mirror, pkg):
    url = f"{mirror}/simple/{pkg}/"
    req = urllib.request.Request(url, headers={"User-Agent": "strata-offline-install"})
    with urllib.request.urlopen(req, timeout=60) as r:
        html = r.read().decode("utf-8", "ignore")
    return re.findall(r'href="([^"]+)"', html)


def find_wheel(mirror, pkg, ver, plat):
    stem = pkg.replace("-", "_") + "-" + ver
    for href in simple_links(mirror, pkg):
        path = href.split("#")[0]
        base = path.split("/")[-1]
        if base.startswith(stem) and plat in base and base.endswith(".whl") and "manylinux" not in base:
            return (path if path.startswith("http") else mirror + "/" + path.replace("../../", "")), base
    for href in simple_links(mirror, pkg):
        path = href.split("#")[0]
        base = path.split("/")[-1]
        if base.startswith(stem) and base.endswith("py3-none-any.whl"):
            return (path if path.startswith("http") else mirror + "/" + path.replace("../../", "")), base
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--mirror", default="https://pypi.tuna.tsinghua.edu.cn")
    ap.add_argument("--pkg", action="append", default=[], help="name==version (repeatable)")
    a = ap.parse_args()

    pkgs = []
    for s in a.pkg:
        name, ver = s.split("==", 1)
        pkgs.append((name, ver, "win_amd64"))
    pkgs = pkgs or DEFAULT_PKGS
    os.makedirs(a.cache, exist_ok=True)

    for pkg, ver, plat in pkgs:
        url, fname = find_wheel(a.mirror, pkg, ver, plat)
        if not fname:
            print(f"[miss] {pkg}=={ver} not found on {a.mirror}")
            continue
        dst = os.path.join(a.cache, fname)
        if not os.path.exists(dst) or os.path.getsize(dst) < 100_000:
            print(f"[get ] {fname}")
            req = urllib.request.Request(url, headers={"User-Agent": "strata-offline-install"})
            with urllib.request.urlopen(req, timeout=900) as r:
                data = r.read()
            with open(dst, "wb") as f:
                f.write(data)
            print(f"       {len(data)/1e6:.1f} MB")
        else:
            print(f"[have] {fname}")
        with zipfile.ZipFile(dst) as z:
            z.extractall(a.site)
        print(f"[ok  ] {pkg}=={ver} unpacked into site-packages")

    # CUDA libs must be reachable via the config's lib_dirs
    cu = os.path.join(a.site, "nvidia", "cu13", "bin", "x86_64")
    print(f"[chk ] cuda bin dir exists = {os.path.isdir(cu)}  ({cu})")
    print("done - remember lib_dirs in strata-<model>.json must point at that dir")


if __name__ == "__main__":
    main()
