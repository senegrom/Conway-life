#!/usr/bin/env python3
"""Regenerate MANIFEST.sha256 over every tracked file.

Hashes are taken over the file's canonical repository content: line endings are
normalised to LF before hashing, so the manifest is identical on Windows (CRLF
checkouts) and on Linux/macOS. Format is the classic

    <sha256>  <path>

sorted by path, matching `sha256sum -c` on a LF checkout.

    python scripts/gen_manifest.py          # rewrite MANIFEST.sha256
    python scripts/gen_manifest.py --check  # verify, exit 1 on drift
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "MANIFEST.sha256"


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True,
                         check=True).stdout
    return sorted(line for line in out.splitlines() if line.strip() and line != "MANIFEST.sha256")


def digest(rel: str) -> str:
    data = (ROOT / rel).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def build() -> str:
    return "".join(f"{digest(rel)}  {rel}\n" for rel in tracked_files())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    text = build()
    if a.check:
        current = MANIFEST.read_text(encoding="utf-8") if MANIFEST.exists() else ""
        if current != text:
            print("MANIFEST.sha256 is out of date; run: python scripts/gen_manifest.py")
            return 1
        print(f"MANIFEST.sha256 up to date ({len(text.splitlines())} files)")
        return 0
    MANIFEST.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {MANIFEST.name}: {len(text.splitlines())} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
