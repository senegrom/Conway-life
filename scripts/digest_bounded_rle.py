#!/usr/bin/env python3
"""Compute the canonical raster digest of a bounded-universe RLE state.

Parses a two-state RLE (with optional #CXRLE Pos offset), maps cells into a
bounded universe whose centre is at coordinate (0, 0) — Golly's bounded-grid
convention, top-left cell at (-W/2, -H/2) for even W, H — and emits the same
canonical digest used by scripts/gen_dense_workload.py and the bb_gol_bench
adapter: SHA-256 over '0'/'1' rows, each terminated by '\\n'.

A cell outside the universe is an error: it means the state was produced with
different universe dimensions or a positioning mistake, and the digest would
be meaningless.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

CXRLE_RE = re.compile(r"^#CXRLE\b.*?Pos\s*=\s*(-?\d+)\s*,\s*(-?\d+)", re.IGNORECASE)
HEADER_RE = re.compile(r"^\s*x\s*=\s*(\d+)\s*,\s*y\s*=\s*(\d+)\s*(?:,\s*rule\s*=\s*(\S+)\s*)?$", re.IGNORECASE)


def parse(text: str) -> tuple[list[tuple[int, int]], int | None, int | None, str | None]:
    pos_x = pos_y = None
    rule = None
    body_parts: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        cx = CXRLE_RE.match(line)
        if cx:
            pos_x, pos_y = int(cx.group(1)), int(cx.group(2))
            continue
        if line.startswith("#"):
            continue
        header = HEADER_RE.match(line)
        if header:
            rule = header.group(3)
            continue
        body_parts.append(line)

    body = "".join(body_parts)
    cells: list[tuple[int, int]] = []
    x = y = 0
    count_text = ""
    terminated = False
    for ch in body:
        if ch.isdigit():
            count_text += ch
            continue
        count = int(count_text) if count_text else 1
        count_text = ""
        if ch in "oA":
            cells.extend((x + dx, y) for dx in range(count))
            x += count
        elif ch in "b.":
            x += count
        elif ch == "$":
            y += count
            x = 0
        elif ch == "!":
            terminated = True
            break
        elif ch.isspace():
            continue
        else:
            raise ValueError(f"unsupported RLE token {ch!r}")
    if not terminated:
        raise ValueError("RLE body must terminate with !")
    return cells, pos_x, pos_y, rule


def bbox_normalised_digest(cells: list[tuple[int, int]]) -> str:
    if not cells:
        return hashlib.sha256(b"").hexdigest()
    min_x = min(x for x, _ in cells)
    min_y = min(y for _, y in cells)
    canonical = "".join(
        f"{x - min_x},{y - min_y}\n"
        for x, y in sorted(cells, key=lambda c: (c[1], c[0]))
    )
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def load_raster(path: Path) -> list[tuple[int, int]]:
    cells = []
    for y, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        for x, ch in enumerate(line):
            if ch == "1":
                cells.append((x, y))
    return cells


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe-width", type=int, required=True)
    parser.add_argument("--universe-height", type=int, required=True)
    parser.add_argument(
        "--match-raster",
        type=Path,
        help="compare bounding-box-normalised content against this '0'/'1' raster "
        "(for RLE files written without a #CXRLE Pos line, e.g. bgolly output)",
    )
    parser.add_argument("rle", type=Path)
    args = parser.parse_args()

    uw, uh = args.universe_width, args.universe_height
    if uw % 2 or uh % 2:
        raise SystemExit("universe dimensions must be even")

    cells, pos_x, pos_y, rule = parse(args.rle.read_text(encoding="utf-8"))

    if args.match_raster is not None:
        raster_cells = load_raster(args.match_raster)
        rle_digest = bbox_normalised_digest(cells)
        raster_digest = bbox_normalised_digest(raster_cells)
        print(
            json.dumps(
                {
                    "rle": str(args.rle),
                    "raster": str(args.match_raster),
                    "rle_population": len(cells),
                    "raster_population": len(raster_cells),
                    "rle_bbox_normalised_sha256": rle_digest,
                    "raster_bbox_normalised_sha256": raster_digest,
                    "match": rle_digest == raster_digest and len(cells) == len(raster_cells),
                },
                indent=2,
            )
        )
        return 0 if rle_digest == raster_digest else 1

    if pos_x is None:
        if cells:
            raise SystemExit("no #CXRLE Pos line: absolute placement unknown for a non-empty state")
        pos_x = pos_y = 0

    rows: dict[int, list[int]] = defaultdict(list)
    for fx, fy in cells:
        ax, ay = fx + pos_x, fy + pos_y
        col, row = ax + uw // 2, ay + uh // 2
        if not (0 <= col < uw and 0 <= row < uh):
            raise SystemExit(f"cell at absolute ({ax},{ay}) outside {uw}x{uh} universe")
        rows[row].append(col)

    hasher = hashlib.sha256()
    empty = b"0" * uw + b"\n"
    for y in range(uh):
        live = rows.get(y)
        if not live:
            hasher.update(empty)
            continue
        line = bytearray(empty)
        for xcol in live:
            line[xcol] = 0x31
        hasher.update(bytes(line))

    print(
        json.dumps(
            {
                "rle": str(args.rle),
                "universe_width": uw,
                "universe_height": uh,
                "rule": rule,
                "population": len(cells),
                "raster_sha256": hasher.hexdigest(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
