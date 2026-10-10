#!/usr/bin/env python3
"""Sign a Windows .exe with YOUR OWN code-signing certificate. Zero install.

Uses only PowerShell cmdlets that ship with Windows (New-SelfSignedCertificate,
Export-PfxCertificate, Set-AuthenticodeSignature) - no Windows SDK, no
signtool.exe, no admin rights.

Read this before you distribute:
  A self-signed certificate makes the signature VALID ON YOUR OWN MACHINE ONLY.
  Anyone else still gets the blue SmartScreen box ("Windows protected your PC").
  To ship to other people without that warning you need a commercial OV
  certificate (~1000-3000 CNY/year). See references/signing-and-smartscreen.md.

Usage:
    python sign_exe.py <file.exe> [--name "Your Name"] [--dir <root>]
                       [--pfx <existing.pfx>] [--password <pw>] [--no-timestamp]
"""

import argparse
import json
import os
import secrets
import subprocess
import sys

DEFAULT_ROOT = os.path.join(os.path.expanduser("~"), ".windowsbuildtools")
TIMESTAMP_SERVER = "http://timestamp.digicert.com"


def resolve_root(explicit):
    """Pick the Windows build-tools root.

    Priority: --dir > WINDOWS_TOOLS_ROOT env > legacy ~/.windows-zero-to-one
    (if it already holds a certs/ folder) > new ~/.windowsbuildtools.
    """
    if explicit:
        return os.path.abspath(explicit)
    env = os.environ.get("WINDOWS_TOOLS_ROOT")
    if env:
        return os.path.abspath(env)
    legacy = os.path.join(os.path.expanduser("~"), ".windows-zero-to-one")
    if os.path.isdir(os.path.join(legacy, "certs")):
        return legacy
    return os.path.join(os.path.expanduser("~"), ".windowsbuildtools")


def log(msg):
    print(msg, flush=True)


def fail(msg):
    print("\n[SIGN FAILED] %s" % msg, file=sys.stderr)
    sys.exit(1)


def ps(script):
    proc = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                           "-Command", script],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode, proc.stdout.decode("utf-8", "replace")


def q(path):
    """Quote a path for a single-quoted PowerShell string."""
    return path.replace("'", "''")


def ensure_cert(root, name, years=5):
    certs = os.path.join(root, "certs")
    os.makedirs(certs, exist_ok=True)
    pfx = os.path.join(certs, "code-signing.pfx")
    props = os.path.join(certs, "signing.properties")
    if os.path.isfile(pfx) and os.path.isfile(props):
        with open(props, encoding="utf-8") as f:
            saved = dict(l.split("=", 1) for l in f.read().splitlines() if "=" in l)
        return pfx, saved.get("password", "")
    password = secrets.token_urlsafe(24)
    script = (
        "$ErrorActionPreference='Stop';"
        "$sec=ConvertTo-SecureString '%s' -AsPlainText -Force;"
        "$c=New-SelfSignedCertificate -Type CodeSigningCert -Subject 'CN=%s' "
        "-KeyAlgorithm RSA -KeyLength 2048 "
        "-CertStoreLocation 'Cert:\\CurrentUser\\My' "
        "-NotAfter (Get-Date).AddYears(%d) -FriendlyName 'Exe signing - %s';"
        "Export-PfxCertificate -Cert $c -FilePath '%s' -Password $sec | Out-Null;"
        "$st=New-Object System.Security.Cryptography.X509Certificates.X509Store "
        "'Root','CurrentUser'; $st.Open('ReadWrite'); $st.Add($c); $st.Close();"
        "$c.Thumbprint" % (password, q(name), years, q(name), q(pfx))
    )
    rc, out = ps(script)
    if rc != 0 or not os.path.isfile(pfx):
        print(out)
        fail("could not create the certificate")
    with open(props, "w", encoding="utf-8") as f:
        f.write("# Local only - never share this file.\n")
        f.write("pfx=%s\n" % pfx.replace("\\", "\\\\"))
        f.write("subject=CN=%s\n" % name)
        f.write("password=%s\n" % password)
    log("  created  %s" % pfx)
    log("  subject  CN=%s" % name)
    return pfx, password


def sign(exe, pfx, password, timestamp=True):
    ts = "-TimestampServer '%s'" % TIMESTAMP_SERVER if timestamp else ""
    script = (
        "$ErrorActionPreference='Stop';"
        "$sec=ConvertTo-SecureString '%s' -AsPlainText -Force;"
        "$c=New-Object System.Security.Cryptography.X509Certificates.X509Certificate2 "
        "-ArgumentList '%s',$sec,'Exportable,PersistKeySet';"
        "$s=Set-AuthenticodeSignature -FilePath '%s' -Certificate $c %s;"
        "$s.Status" % (password, q(pfx), q(exe), ts)
    )
    rc, out = ps(script)
    status = out.strip().splitlines()[-1].strip() if out.strip() else ""
    return rc, status, out


def verify(exe):
    rc, out = ps("(Get-AuthenticodeSignature '%s').Status" % q(exe))
    return out.strip().splitlines()[-1].strip() if out.strip() else "Unknown"


def main():
    ap = argparse.ArgumentParser(description="Sign a Windows exe.")
    ap.add_argument("exe", help="the .exe to sign")
    ap.add_argument("--name", default=None, help="certificate subject (default: your username)")
    ap.add_argument("--dir", default=None, help="root holding certs/ (default %s)" % DEFAULT_ROOT)
    ap.add_argument("--pfx", default=None, help="use an existing pfx instead of generating one")
    ap.add_argument("--password", default=None, help="pfx password")
    ap.add_argument("--no-timestamp", action="store_true",
                    help="skip the timestamp server (offline machines)")
    args = ap.parse_args()

    exe = os.path.abspath(args.exe)
    if not os.path.isfile(exe):
        fail("no such file: %s" % exe)
    root = resolve_root(args.dir)
    name = args.name or os.environ.get("USERNAME") or os.environ.get("USER") or "exe-builder"

    log("=" * 58)
    log(" Signing %s" % os.path.basename(exe))
    log("=" * 58)

    if args.pfx:
        pfx, password = os.path.abspath(args.pfx), args.password
        if not password:
            fail("--pfx requires --password")
        log("  using existing certificate %s" % pfx)
    else:
        pfx, password = ensure_cert(root, name)

    rc, status, out = sign(exe, pfx, password, timestamp=not args.no_timestamp)
    if status != "Valid" and not args.no_timestamp:
        log("  timestamp server unreachable, signing without it")
        rc, status, out = sign(exe, pfx, password, timestamp=False)
    if status != "Valid":
        print(out)
        fail("signature status is '%s', expected Valid" % status)

    final = verify(exe)
    log("")
    log("=" * 58)
    log(" SIGNED   %s" % exe)
    log("  status  %s" % final)
    log("  cert    CN=%s" % name)
    log("=" * 58)
    log("")
    log(" Heads up: this is a SELF-SIGNED certificate.")
    log("  * Valid on this machine because the cert was added to your"
       " Trusted Root store.")
    log("  * On anyone else's machine SmartScreen still shows the blue box.")
    log("  * Shipping to others without that warning needs a commercial OV cert.")
    log("  * Back up certs/code-signing.pfx + signing.properties together.")
    log("=" * 58)


if __name__ == "__main__":
    main()
