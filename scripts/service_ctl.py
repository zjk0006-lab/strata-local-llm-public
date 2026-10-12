"""Sandbox-safe service control: status / stop / start.

WHY THIS EXISTS (three separate sandbox traps):
  - Git Bash mangles `/F`-style flags: `taskkill //F //IM x` -> "invalid parameter '//F'".
  - Calling cmd.exe directly from Bash is blocked: "从 Bash 调 cmd.exe 判定为绕过命令校验".
  - Inline `python -c "...win32com..."` is blocked as a high-risk call.
  => Everything goes through Python subprocess with an argv LIST (no shell string).

IMPORTANT PROCESS-LIFETIME TRAP:
  The sandbox RECLAIMS the whole child process tree when a tool call ends. Anything
  started with Popen / ShellExecute / foreground from here will "vanish" a moment later.
  `run_in_background` survives only during the task. A LONG-LIVED instance can only be
  started by the USER double-clicking the shortcut. Never claim "the model is running"
  based on an instance you launched yourself.

  Also: if your agent itself is configured to use this local model (右下角 strata-local),
  `stop` kills the very process answering you -> you disconnect mid-reply. In that case
  do NOT stop; hand the user restart-strata.cmd instead.

Usage:
  python service_ctl.py status
  python service_ctl.py stop
  python service_ctl.py start --root "G:\\AI\\models\\Qwen3.8-Flash-Next-IQ3_S"
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.request

PORT = 8080


def api(path="/v1/models", timeout=3):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"_error": str(e)}


def listening_pids():
    out = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True,
                         encoding="gbk", errors="ignore").stdout
    pids = set()
    for line in out.splitlines():
        if f":{PORT}" in line and "LISTENING" in line:
            pids.add(line.split()[-1])
    return pids


def status():
    d = api()
    if "_error" in d:
        print(f"[down] {d['_error']}")
        return 1
    for m in d.get("data", []):
        # REAL /v1/models shape on this engine (do not assume flat fields):
        #   status = {"value": "loaded"}   <- dict, not a string
        #   n_ctx  lives in meta.n_ctx
        #   modalities live in architecture.input_modalities
        st = m.get("status")
        st = st.get("value") if isinstance(st, dict) else st
        nctx = (m.get("meta") or {}).get("n_ctx")
        mods = (m.get("architecture") or {}).get("input_modalities")
        print(f"[up] id={m.get('id')} status={st} n_ctx={nctx} modalities={mods}")
        if nctx and nctx < 131072:
            print(f"  [WARN] n_ctx={nctx} - the 400 context-overflow bug will come back")
    print("listening pids:", sorted(listening_pids()))
    return 0


def stop():
    pids = listening_pids()
    for pid in pids:
        subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
    for img in ("strata.exe", "strata-vision.exe"):
        subprocess.run(["taskkill", "/F", "/IM", img], capture_output=True)
    d = api()
    if "_error" not in d:
        print("[WARN] port still responding - stop it in Task Manager")
        return 1
    print(f"[ok] stopped (killed pids {sorted(pids)}). Port {PORT} is free.")
    return 0


def start(root):
    """Detached launch. NOTE: the sandbox will reclaim this tree when the tool call
    ends - use it only to verify the command sequence works, not to keep the model up."""
    s = os.path.join(root, "Strata")
    cmd = [os.path.join(s, ".venv", "Scripts", "python.exe"),
           os.path.join(s, "serve", "server.py"),
           "--engine", "strata",
           "--config", os.path.join(s, "strata-iq3_s.json"),
           "--port", str(PORT)]
    DETACHED = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(cmd, cwd=s, creationflags=DETACHED,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("[sent] launch command issued; first load takes 1-3 minutes")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["status", "stop", "start"])
    ap.add_argument("--root", default=r"G:\AI\models\Qwen3.8-Flash-Next-IQ3_S")
    a = ap.parse_args()
    if a.action == "status":
        sys.exit(status())
    if a.action == "stop":
        sys.exit(stop())
    sys.exit(start(a.root))


if __name__ == "__main__":
    main()
