"""Generate start/stop/restart .cmd launchers for a Strata model deployment.

CRITICAL encoding law on this machine: .cmd/.bat must be PURE ASCII + CRLF.
Chinese (UTF-8 no BOM) or LF line endings make cmd.exe parse them as GBK -> garbled,
and files forwarded over WeChat/mail also get a Zone.Identifier block.
That is exactly why "the bat doesn't work when sent over".

Usage:
  python make_launchers.py --root "G:\\AI\\models\\Qwen3.8-Flash-Next-IQ3_S" [--port 8080]
"""
import argparse
import os

START = """@echo off
title Strata - {name}
set "S={strata}"
curl.exe -s -m 2 http://127.0.0.1:{port}/v1/models >nul 2>&1
if %errorlevel%==0 (
  echo Strata is already running. Opening http://127.0.0.1:{port} ...
  start "" http://127.0.0.1:{port}
  timeout /t 3 /nobreak >nul
  exit /b 0
)
echo.
echo  Starting Strata - {name}
echo  First load takes 1-3 minutes. Keep this window open to keep it running.
echo.
cd /d "%S%"
"{py}" "{server}" --engine strata --config "{config}" --port {port} --open
echo.
echo  Strata stopped.
pause
"""

STOP = """@echo off
title Stop Strata - {name}

curl.exe -s -m 2 http://127.0.0.1:{port}/v1/models >nul 2>&1
if %errorlevel% neq 0 (
  echo.
  echo  Strata is not running.
  echo.
  timeout /t 3 /nobreak >nul
  exit /b 0
)

echo.
echo  Stopping Strata ...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":{port}" ^| findstr LISTENING') do taskkill /F /PID %%p >nul 2>&1
taskkill /F /IM strata.exe >nul 2>&1
taskkill /F /IM strata-vision.exe >nul 2>&1
timeout /t 2 /nobreak >nul

curl.exe -s -m 2 http://127.0.0.1:{port}/v1/models >nul 2>&1
if %errorlevel% equ 0 (
  echo  [WARN] Port {port} is still responding. Stop it manually in Task Manager.
) else (
  echo  Strata stopped. Port {port} is free.
)
echo.
timeout /t 4 /nobreak >nul
"""

RESTART = """@echo off
title Restart Strata
set "S={strata}"
echo Stopping old service ...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":{port}" ^| findstr LISTENING') do taskkill /F /PID %%p >nul 2>&1
taskkill /F /IM strata.exe >nul 2>&1
taskkill /F /IM strata-vision.exe >nul 2>&1
timeout /t 3 /nobreak >nul
echo Starting with the current config ...
cd /d "%S%"
start "Strata" "{py}" "{server}" --engine strata --config "{config}" --port {port} --open
echo Done. First load takes 1-3 minutes.
timeout /t 6
"""


def write_ascii_crlf(path, text):
    """Force pure ASCII + CRLF. Never write Chinese into a .cmd on this machine."""
    data = text.replace("\r\n", "\n").replace("\n", "\r\n").encode("ascii")
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="model dir, e.g. G:\\AI\\models\\Qwen3.8-Flash-Next-IQ3_S")
    ap.add_argument("--port", default="8080")
    ap.add_argument("--name", default="Qwen3.8-Flash-Next IQ3_S")
    a = ap.parse_args()

    root = os.path.abspath(a.root)
    strata = os.path.join(root, "Strata")
    ctx = {
        "name": a.name,
        "port": a.port,
        "strata": strata,
        "py": os.path.join(strata, ".venv", "Scripts", "python.exe"),
        "server": os.path.join(strata, "serve", "server.py"),
        "config": os.path.join(strata, "strata-iq3_s.json"),
    }
    for fn, tpl in (("start-strata.cmd", START), ("stop-strata.cmd", STOP), ("restart-strata.cmd", RESTART)):
        p = os.path.join(root, fn)
        n = write_ascii_crlf(p, tpl)
        # self-check: no bare LF, pure ASCII
        raw = open(p, "rb").read()
        bare_lf = raw.count(b"\n") - raw.count(b"\r\n")
        print(f"[ok] {fn}  {n} B  bare_LF={bare_lf}")
        assert bare_lf == 0, "CRLF enforcement failed"


if __name__ == "__main__":
    main()
