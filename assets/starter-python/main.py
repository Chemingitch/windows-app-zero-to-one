"""Minimal Windows exe skeleton.

Build:  python scripts/build_exe.py --src . --noconsole
Direct: pyinstaller --onefile --noconsole main.py
"""

import argparse
import os
import sys

VERSION = "1.0.0"


def config_dir():
    """%APPDATA%\\MyApp - the safe place to write user data."""
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "MyApp")
    os.makedirs(d, exist_ok=True)
    return d


def main():
    ap = argparse.ArgumentParser(description="My app")
    ap.add_argument("--version", action="store_true", help="print version and exit")
    args = ap.parse_args()

    if args.version:
        print("myapp %s" % VERSION)
        return 0

    print("myapp is running")
    print("config dir:", config_dir())
    return 0


if __name__ == "__main__":
    sys.exit(main())
