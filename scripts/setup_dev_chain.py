#!/usr/bin/env python3
"""Bootstrap a Windows exe toolchain. No IDE, no Visual Studio, no admin rights.

Everything is unpacked into a single directory under your user profile and
recorded in <root>/devchain.json, so build_exe.py finds it with no flags.

Usage:
    python setup_dev_chain.py [--lang go|dotnet|python|all] [--dir <root>]
                              [--proxy http://host:port] [--dry-run]

  go      ~70 MB, unpack-and-run. Best for a single self-contained exe.
  dotnet  ~200 MB via the official install script. Best for real GUI apps.
  python  reuses the current interpreter, installs PyInstaller into it.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

GO_VERSION_URL = "https://go.dev/VERSION?m=text"
GO_FALLBACK = ["go1.22.5", "go1.21.11"]
GO_DL = "https://dl.google.com/go/%s.windows-amd64.zip"
DOTNET_INSTALL = "https://dot.net/v1/dotnet-install.ps1"
DOTNET_CHANNEL = "8.0"

DEFAULT_ROOT = os.path.join(os.path.expanduser("~"), ".windowsbuildtools")


def log(msg):
    print(msg, flush=True)


def fail(msg):
    print("\n[SETUP FAILED] %s" % msg, file=sys.stderr)
    sys.exit(1)


def download(url, dest, proxy=None, label=""):
    log("  downloading %s" % (label or url))
    if proxy:
        os.environ["https_proxy"] = proxy
        os.environ["http_proxy"] = proxy
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = r.read(262144)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if total:
                    sys.stdout.write("\r    %d / %d KB" % (done // 1024, total // 1024))
                    sys.stdout.flush()
            sys.stdout.write("\n")
    except Exception as e:
        return False, str(e)
    return True, ""


def fetch_text(url, proxy=None):
    if proxy:
        os.environ["https_proxy"] = proxy
        os.environ["http_proxy"] = proxy
    try:
        with urllib.request.urlopen(urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
            return r.read().decode("utf-8", "replace").strip()
    except Exception:
        return ""


def setup_go(root, proxy):
    go_home = os.path.join(root, "go")
    go_exe = os.path.join(go_home, "bin", "go.exe")
    if os.path.isfile(go_exe):
        log("  already present: %s" % go_exe)
        return go_home
    ver = fetch_text(GO_VERSION_URL, proxy).split("\n")[0].strip()
    candidates = ([ver] if ver.startswith("go") else []) + GO_FALLBACK
    os.makedirs(root, exist_ok=True)
    for v in candidates:
        tmp = os.path.join(tempfile.mkdtemp(), "go.zip")
        ok, err = download(GO_DL % v, tmp, proxy, v)
        if not ok:
            log("  %s unavailable: %s" % (v, err))
            continue
        with zipfile.ZipFile(tmp) as z:
            z.extractall(root)
        os.remove(tmp)
        if os.path.isfile(go_exe):
            return go_home
    fail("could not install Go. Check the network or pass --proxy.")


def setup_dotnet(root, proxy):
    dotnet_home = os.path.join(root, "dotnet")
    dotnet_exe = os.path.join(dotnet_home, "dotnet.exe")
    if os.path.isfile(dotnet_exe):
        log("  already present: %s" % dotnet_exe)
        return dotnet_home
    os.makedirs(root, exist_ok=True)
    ps1 = os.path.join(root, "dotnet-install.ps1")
    ok, err = download(DOTNET_INSTALL, ps1, proxy, "dotnet-install.ps1")
    if not ok:
        fail("could not fetch dotnet-install.ps1: %s" % err)
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1,
           "-Channel", DOTNET_CHANNEL, "-InstallDir", dotnet_home, "-NoPath"]
    if proxy:
        cmd += ["-ProxyAddress", proxy]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = proc.stdout.decode("utf-8", "replace")
    if proc.returncode != 0 or not os.path.isfile(dotnet_exe):
        print(out[-2000:])
        fail("dotnet install failed")
    return dotnet_home


def setup_python(root):
    py = sys.executable
    if not py:
        fail("no python interpreter found")
    log("  interpreter: %s" % py)
    proc = subprocess.run([py, "-m", "pip", "install", "--upgrade", "pyinstaller"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = proc.stdout.decode("utf-8", "replace")
    if proc.returncode != 0:
        print(out[-2000:])
        fail("pip install pyinstaller failed (try adding --proxy and re-running)")
    log("  pyinstaller ready")
    return py


def main():
    ap = argparse.ArgumentParser(description="Bootstrap a Windows exe toolchain.")
    ap.add_argument("--lang", choices=["go", "dotnet", "python", "all"], default="go",
                    help="what to install (default: go)")
    ap.add_argument("--dir", default=None, help="install root (default %s)" % DEFAULT_ROOT)
    ap.add_argument("--proxy", default=None, help="http proxy, e.g. http://127.0.0.1:7890")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = os.path.abspath(args.dir or os.environ.get("WINDOWS_TOOLS_ROOT") or DEFAULT_ROOT)
    log("=" * 58)
    log(" Windows exe toolchain bootstrap")
    log("  lang = %s" % args.lang)
    log("  root = %s" % root)
    log("=" * 58)

    if args.dry_run:
        log(" dry run - nothing was downloaded")
        return

    cfg = {}
    legacy = os.path.join(os.path.expanduser("~"), ".windows-zero-to-one")
    for cand in (os.path.join(root, "devchain.json"),
                os.path.join(legacy, "devchain.json")):
        if os.path.isfile(cand):
            try:
                with open(cand, encoding="utf-8") as f:
                    cfg = json.load(f)
                break
            except Exception:
                cfg = {}

    langs = ["go", "dotnet", "python"] if args.lang == "all" else [args.lang]
    for i, lang in enumerate(langs, 1):
        log("[%d/%d] %s" % (i, len(langs), lang))
        if lang == "go":
            cfg["go"] = setup_go(root, args.proxy)
        elif lang == "dotnet":
            cfg["dotnet"] = setup_dotnet(root, args.proxy)
        else:
            cfg["python"] = setup_python(root)

    os.makedirs(root, exist_ok=True)
    with open(os.path.join(root, "devchain.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    log("")
    log("=" * 58)
    log(" READY")
    for k, v in cfg.items():
        log("   %-8s %s" % (k, v))
    log(" config written to %s" % os.path.join(root, "devchain.json"))
    log("")
    log(" Next:  python build_exe.py --src <project>")
    log("        python sign_exe.py <file.exe>")
    log("=" * 58)


if __name__ == "__main__":
    main()
