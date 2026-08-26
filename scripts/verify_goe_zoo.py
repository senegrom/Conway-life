#!/usr/bin/env python3
"""Independently verify the known Garden of Eden zoo and compute flip points.

Fetches nine published Garden of Eden patterns from the conwaylife.appspot.com
pattern library (page-embedded JSON; provenance pinned by SHA-256 prefix of
the RLE body), then for each:

  1. verifies with scripts/preimage_sat.py that the bare bounding-box pattern
     is an ORPHAN (no radius-1 preimage patch) — the defining property, checked
     end-to-end by our own exhaustively validated encoding;
  2. reports the Salo-Törmä flip point f(P) (padding_flip.py), which is 0 for
     an orphan.

Result recorded 2026-08-26: all nine are orphans (f = 0), including Banks'
1971 original — so the bounding-box patterns of known GoEs provide no
improvement to the padding-constant lower bound of Q28820954, and the
preimage checker's UNSAT path is validated against nine independent published
artifacts.

Patterns are third-party content; they are fetched, not committed. Requires
python-sat and network access.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preimage_sat as ps
import reference_life as life
from padding_flip import flip_point

ZOO: list[tuple[str, str, str]] = [
    ("gardenofeden1", "33x9", "f8292a6adbb3bfb0"),
    ("gardenofeden2", "14x14", "746036773461ab42"),
    ("gardenofeden3", "13x12", "beff0f949cb68262"),
    ("gardenofeden4", "12x11", "05d2854f944edba3"),
    ("gardenofeden5", "11x11", "358df009199f9407"),
    ("gardenofeden6", "11x10", "a8cdb938c680aa93"),
    ("gardenofeden45cells", "11x11", "ae6ae25fe811cb61"),
    ("gardenofeden11", "11x9", "ff08691684222731"),
    ("gardenofeden5x45", "45x5", "099399c6ab358318"),
]

BASE = "https://conwaylife.appspot.com/pattern/"


def fetch_pattern(name: str) -> dict:
    req = urllib.request.Request(BASE + name, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    m = re.search(r"var pattern = (\{[^}]*\})", html)
    if not m:
        raise SystemExit(f"{name}: no embedded pattern data found")
    return json.loads(m.group(1))


def main() -> int:
    failures = 0
    for name, size, digest16 in ZOO:
        info = fetch_pattern(name)
        got_digest = hashlib.sha256(info["data"].encode("ascii")).hexdigest()[:16]
        if info["size"] != size or got_digest != digest16:
            print(f"{name}: PROVENANCE MISMATCH (size {info['size']}, sha {got_digest}) — upstream changed")
            failures += 1
            continue
        w, h = map(int, size.split("x"))
        pattern = life.parse_rle_text(f"x = {w}, y = {h}, rule = B3/S23\n{info['data']}\n")
        raster = [[0] * w for _ in range(h)]
        for x, y in pattern.live:
            raster[y][x] = 1
        has, _ = ps.check_window(raster)
        f = flip_point(raster)
        ok = (not has) and f == 0
        if not ok:
            failures += 1
        print(
            f"{name} ({size}, pop {len(pattern.live)}): "
            f"{'ORPHAN verified' if not has else 'NOT an orphan?!'}, f(P) = {f}"
        )
    print("FAILURES:", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
