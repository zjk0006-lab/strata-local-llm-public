"""Health check + speed baseline + vision path test for the local Strata model.

Do NOT trust "the process exists" as proof of health. Check:
  - /v1/models returns status=loaded and the EXPECTED n_ctx (262144 after the fix)
  - a short answer and a long answer, each timed -> tok/s
  - a tiny generated PNG sent as an image_url data URI -> the vision path works

THINKING-TOKEN TRAP: this model thinks. With max_tokens <= 300 the whole budget can be
consumed by thinking and the answer comes back EMPTY (log: "the reply reached max tokens
while still thinking, so it has no answer"). Use max_tokens >= 800, or set
reasoning_budget_tokens to cap thinking explicitly.

Usage:
  python verify_service.py [--port 8080] [--model qwen3.8-flash-next-iq3_s] [--skip-vision]
"""
import argparse
import base64
import json
import struct
import time
import urllib.request
import zlib

PORT = 8080
MODEL = "qwen3.8-flash-next-iq3_s"


def chat(prompt, max_tokens=900, timeout=180, image=None):
    msgs = [{"role": "user", "content": prompt}]
    if image:
        msgs[0]["content"] = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + image}},
        ]
    body = json.dumps({"model": MODEL, "messages": msgs, "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions",
                                 data=body, headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    dt = time.time() - t0
    txt = d["choices"][0]["message"].get("content") or ""
    usage = d.get("usage", {})
    n = usage.get("completion_tokens") or len(txt)
    return txt, n, dt, (n / dt if dt else 0)


def tiny_png():
    """64x64 white canvas with a red rectangle - built with zlib+struct, no PIL."""
    W = H = 64

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    raw = bytearray()
    for y in range(H):
        raw.append(0)
        for x in range(W):
            red = 16 <= x < 48 and 20 <= y < 44
            raw += bytes((214, 62, 62, 255) if red else (255, 255, 255, 255))
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))
    return base64.b64encode(png).decode()


def main():
    global PORT, MODEL
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--skip-vision", action="store_true")
    a = ap.parse_args()
    PORT, MODEL = a.port, a.model

    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/v1/models", timeout=5) as r:
        d = json.loads(r.read())
    for m in d.get("data", []):
        # REAL shape: status is {"value": "loaded"}, n_ctx is under meta,
        # modalities under architecture.input_modalities. Don't assume flat fields.
        st = m.get("status")
        st = st.get("value") if isinstance(st, dict) else st
        nctx = (m.get("meta") or {}).get("n_ctx")
        mods = (m.get("architecture") or {}).get("input_modalities")
        print(f"[models] id={m.get('id')} status={st} n_ctx={nctx} modalities={mods}")
        if nctx and nctx < 131072:
            print("  [WARN] n_ctx is small - the 400 context-overflow bug will come back")

    txt, n, dt, tps = chat("用一句话解释什么是 MoE（混合专家）模型。")
    print(f"[short] {n} tok / {dt:.1f}s = {tps:.1f} tok/s  empty={not txt.strip()}")

    txt, n, dt, tps = chat("详细列出本地大模型推理的常见优化手段，每种给一句适用条件说明。",
                           max_tokens=1200)
    print(f"[long ] {n} tok / {dt:.1f}s = {tps:.1f} tok/s  empty={not txt.strip()}")

    if not a.skip_vision:
        try:
            txt, n, dt, tps = chat("图里有什么？", image=tiny_png())
            print(f"[vision] {n} tok / {dt:.1f}s = {tps:.1f} tok/s  answer={txt.strip()[:80]!r}")
        except Exception as e:
            print(f"[vision] FAILED: {e}")

    print("\nbaseline on this box: short 30-50 tok/s, long 60-89 tok/s; HDD-resident weights = 3 tok/s")


if __name__ == "__main__":
    main()
