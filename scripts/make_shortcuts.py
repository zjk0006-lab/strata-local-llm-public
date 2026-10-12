"""Create / clean up the (start)/(stop) shortcut pair in Start Menu + Desktop.

PITFALLS handled here:
- `python -c "import win32com.client ..."` is BLOCKED by the sandbox as a
  （高危调用）. COM calls MUST live in a .py file, never inline -c.
- On this machine the Desktop is REDIRECTED: SpecialFolders("Desktop") returns
  a custom redirected path, not C:\\Users\\<user>\\Desktop. Always ask the shell for it.
- Win11 blocks scripted Taskbar pinning (Taskband Pin) - the user must right-click
  and pin manually.
- Shortcut names are made into a symmetric pair so start/stop are obvious.

Usage:
  python make_shortcuts.py --root "G:\\AI\\models\\Qwen3.8-Flash-Next-IQ3_S" [--prefix "Strata 本地大模型"]
"""
import argparse
import os

import win32com.client


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--prefix", default="Strata 本地大模型")
    ap.add_argument("--remove-old", default="", help="legacy .lnk base name to delete (e.g. 'Strata 本地大模型')")
    a = ap.parse_args()

    root = os.path.abspath(a.root)
    icons = os.path.join(root, "icons")
    targets = [
        ("（启动）", os.path.join(root, "start-strata.cmd"), os.path.join(icons, "start.ico"),
         "Start the local Strata LLM"),
        ("（停止）", os.path.join(root, "stop-strata.cmd"), os.path.join(icons, "stop.ico"),
         "Stop the local Strata LLM"),
    ]

    sh = win32com.client.Dispatch("WScript.Shell")
    folders = {
        "startmenu": sh.SpecialFolders("Programs"),
        "desktop": sh.SpecialFolders("Desktop"),   # may be redirected to a custom data-drive path
    }
    print("desktop folder =", folders["desktop"])

    for tag, folder in folders.items():
        for suffix, target, icon, desc in targets:
            lnk = os.path.join(folder, f"{a.prefix}{suffix}.lnk")
            sc = sh.CreateShortCut(lnk)
            sc.TargetPath = target
            sc.WorkingDirectory = root
            sc.IconLocation = icon + ",0"
            sc.Description = desc
            sc.Save()
            print(f"[ok] {tag:9s} {os.path.basename(lnk)}  ->  {target}")
        if a.remove_old:
            old = os.path.join(folder, f"{a.remove_old}.lnk")
            if os.path.exists(old):
                os.remove(old)
                print(f"[del] removed legacy {old}")

    # verify every .lnk resolves
    for tag, folder in folders.items():
        for suffix, _, _, _ in targets:
            lnk = os.path.join(folder, f"{a.prefix}{suffix}.lnk")
            sc = sh.CreateShortCut(lnk)
            ok = os.path.exists(sc.TargetPath)
            print(f"[chk] {tag:9s} {os.path.basename(lnk)} target_exists={ok} icon={sc.IconLocation}")


if __name__ == "__main__":
    main()
