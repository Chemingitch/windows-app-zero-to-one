#!/usr/bin/env python3
"""Build a single Windows .exe from source. Detects the language, no IDE needed.

Detects: go.mod -> go build | *.csproj -> dotnet publish | *.py -> PyInstaller.

Usage:
    python build_exe.py --src <project-dir> [--out <file.exe>] [--name app]
                        [--lang go|dotnet|python] [--noconsole] [--sign]

Toolchain is resolved from devchain.json (written by setup_dev_chain.py),
then PATH, then --go/--dotnet/--python flags.
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys

DEFAULT_ROOT = os.path.join(os.path.expanduser("~"), ".windows-zero-to-one")


def log(msg):
    print(msg, flush=True)


def fail(msg):
    print("\n[BUILD FAILED] %s" % msg, file=sys.stderr)
    sys.exit(1)


def sh(args, cwd=None, env=None, quiet=False):
    if not quiet:
        log("  -> %s" % " ".join(args[:4]))
    proc = subprocess.run(args, cwd=cwd, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = proc.stdout.decode("utf-8", "replace")
    if proc.returncode != 0:
        print(out[-3000:])
        fail("step failed (%d)" % proc.returncode)
    return out


def load_devchain():
    roots = []
    v = os.environ.get("WINDOWS_TOOLS_ROOT")
    if v:
        roots.append(v)
    roots.append(DEFAULT_ROOT)
    for r in roots:
        p = os.path.join(r, "devchain.json")
        if os.path.isfile(p):
            try:
                with open(p, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}


def detect_lang(src, forced=None):
    if forced:
        return forced
    if os.path.isfile(os.path.join(src, "go.mod")):
        return "go"
    if glob.glob(os.path.join(src, "*.csproj")) or glob.glob(os.path.join(src, "*.sln")):
        return "dotnet"
    if glob.glob(os.path.join(src, "*.py")):
        return "python"
    fail("cannot detect project type in %s (no go.mod / *.csproj / *.py). "
         "Pass --lang go|dotnet|python." % src)


def build_go(src, out, cfg, go_home):
    go_home = go_home or cfg.get("go")
    if not go_home or not os.path.isfile(os.path.join(go_home, "bin", "go.exe")):
        fail("Go not found. Run setup_dev_chain.py --lang go first.")
    go = os.path.join(go_home, "bin", "go.exe")
    env = os.environ.copy()
    env["GOROOT"] = go_home
    env["GOPATH"] = os.path.join(os.path.dirname(go_home), "gopath")
    env["CGO_ENABLED"] = "0"
    env["GOFLAGS"] = "-buildvcs=false"
    os.makedirs(env["GOPATH"], exist_ok=True)
    cmd = [go, "build", "-trimpath", "-ldflags", "-s -w", "-o", out, "."]
    log("  -> %s" % " ".join(cmd[:3]))
    proc = subprocess.run(cmd, cwd=src, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        print(proc.stdout.decode("utf-8", "replace")[-3000:])
        fail("go build failed")
    return out


def build_dotnet(src, out, cfg, dotnet_home):
    dotnet_home = dotnet_home or cfg.get("dotnet")
    dotnet = os.path.join(dotnet_home, "dotnet.exe") if dotnet_home else shutil.which("dotnet")
    if not dotnet or not os.path.isfile(dotnet):
        fail(".NET not found. Run setup_dev_chain.py --lang dotnet first.")
    outdir = os.path.dirname(out)
    os.makedirs(outdir, exist_ok=True)
    cmd = [dotnet, "publish", src, "-c", "Release", "-r", "win-x64",
           "--self-contained", "true",
           "-p:PublishSingleFile=true",
           "-p:IncludeNativeLibrariesForSelfExtract=true",
           "-p:EnableCompressionInSingleFile=true",
           "-o", outdir]
    log("  -> dotnet publish (this is slow the first time)")
    proc = subprocess.run(cmd, cwd=src, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    res = proc.stdout.decode("utf-8", "replace")
    if proc.returncode != 0:
        print(res[-3000:])
        fail("dotnet publish failed")
    built = os.path.join(outdir, os.path.basename(out))
    if not os.path.isfile(built):
        exes = glob.glob(os.path.join(outdir, "*.exe"))
        if not exes:
            fail("publish produced no exe")
        shutil.move(exes[0], built)
    return built


def build_python(src, out, cfg, py):
    py = py or cfg.get("python") or sys.executable
    proc = subprocess.run([py, "-c", "import PyInstaller"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        fail("PyInstaller missing. Run setup_dev_chain.py --lang python first.")
    name = os.path.splitext(os.path.basename(out))[0]
    cmd = [py, "-m", "PyInstaller", "--onefile", "--clean", "--name", name]
    if args_noconsole:
        cmd.append("--noconsole")
    entry = os.path.join(src, "main.py")
    if not os.path.isfile(entry):
        pys = sorted(glob.glob(os.path.join(src, "*.py")))
        if not pys:
            fail("no .py entry point")
        entry = pys[0]
    cmd.append(entry)
    dist = os.path.join(src, "dist")
    sh(cmd, cwd=src)
    built = os.path.join(dist, name + ".exe")
    if not os.path.isfile(built):
        fail("PyInstaller produced no exe")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    shutil.move(built, out)
    return out


args_noconsole = False


def main():
    ap = argparse.ArgumentParser(description="Build a Windows exe from source.")
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", default=None, help="output exe (default <src>/dist/app.exe)")
    ap.add_argument("--name", default=None, help="exe basename (default: project dir name)")
    ap.add_argument("--lang", choices=["go", "dotnet", "python"], default=None)
    ap.add_argument("--noconsole", action="store_true", help="GUI app (python only)")
    ap.add_argument("--go", default=None, help="override GOROOT")
    ap.add_argument("--dotnet", default=None, help="override dotnet home")
    ap.add_argument("--python", default=None, help="override python interpreter")
    ap.add_argument("--sign", action="store_true", help="sign after building")
    args = ap.parse_args()

    global args_noconsole
    args_noconsole = args.noconsole

    src = os.path.abspath(args.src)
    if not os.path.isdir(src):
        fail("no such directory: %s" % src)
    name = args.name or os.path.basename(src)
    out = os.path.abspath(args.out or os.path.join(src, "dist", name + ".exe"))
    os.makedirs(os.path.dirname(out), exist_ok=True)

    lang = detect_lang(src, args.lang)
    cfg = load_devchain()
    log("=" * 58)
    log(" Windows exe build   src=%s" % src)
    log("  lang = %s" % lang)
    log("=" * 58)

    if lang == "go":
        result = build_go(src, out, cfg, args.go)
    elif lang == "dotnet":
        result = build_dotnet(src, out, cfg, args.dotnet)
    else:
        result = build_python(src, out, cfg, args.python)

    log("")
    log("=" * 58)
    log(" BUILD OK -> %s (%d bytes)" % (result, os.path.getsize(result)))
    log("=" * 58)

    if args.sign:
        signer = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sign_exe.py")
        if os.path.isfile(signer):
            subprocess.run([sys.executable, signer, result])
        else:
            log(" (sign_exe.py not found next to this script)")


if __name__ == "__main__":
    main()
