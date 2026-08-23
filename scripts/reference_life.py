#!/usr/bin/env python3
"""Small, trusted Conway Life reference implementation.

This is intentionally simple rather than fast. It supports finite live-cell
sets on the unbounded plane and the common two-state subset of RLE. Use it for
correctness checks, never for performance comparisons.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Iterable

Cell = tuple[int, int]
HEADER_RE = re.compile(
    r"^\s*x\s*=\s*(\d+)\s*,\s*y\s*=\s*(\d+)(?:\s*,\s*rule\s*=\s*([^,\s]+))?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RLEPattern:
    live: frozenset[Cell]
    width: int | None = None
    height: int | None = None
    rule: str = "B3/S23"


def normalise_rule(rule: str) -> str:
    cleaned = rule.upper().replace(" ", "")
    if cleaned in {"LIFE", "B3/S23", "B3S23", "S23/B3"}:
        return "B3/S23"
    raise ValueError(f"Reference implementation supports B3/S23 only, got {rule!r}")


def parse_rle_text(text: str) -> RLEPattern:
    """Parse a standard two-state RLE file."""
    width: int | None = None
    height: int | None = None
    rule = "B3/S23"
    body_parts: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = HEADER_RE.fullmatch(line)
        if match:
            width = int(match.group(1))
            height = int(match.group(2))
            if match.group(3):
                rule = normalise_rule(match.group(3))
            continue
        body_parts.append(line)

    if width is None or height is None:
        raise ValueError("RLE header with x and y is required")

    body = "".join(body_parts)
    live: set[Cell] = set()
    x = 0
    y = 0
    count_text = ""
    terminated = False

    for ch in body:
        if ch.isdigit():
            count_text += ch
            continue
        count = int(count_text) if count_text else 1
        count_text = ""

        if ch in "oA":
            for dx in range(count):
                live.add((x + dx, y))
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
            raise ValueError(f"Unsupported RLE token: {ch!r}")

    if not terminated:
        raise ValueError("RLE body must terminate with !")
    if any(x0 < 0 or y0 < 0 or x0 >= width or y0 >= height for x0, y0 in live):
        raise ValueError("live cell lies outside declared RLE dimensions")

    return RLEPattern(frozenset(live), width, height, normalise_rule(rule))


def read_rle(path: Path) -> RLEPattern:
    return parse_rle_text(path.read_text(encoding="utf-8"))


def step(live: Iterable[Cell]) -> frozenset[Cell]:
    """Advance one B3/S23 generation on the unbounded plane."""
    live_set = set(live)
    counts: Counter[Cell] = Counter()
    for x, y in live_set:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx or dy:
                    counts[(x + dx, y + dy)] += 1

    return frozenset(
        cell
        for cell, neighbours in counts.items()
        if neighbours == 3 or (neighbours == 2 and cell in live_set)
    )


def advance(live: Iterable[Cell], generations: int) -> frozenset[Cell]:
    if generations < 0:
        raise ValueError("generations must be non-negative")
    state = frozenset(live)
    for _ in range(generations):
        state = step(state)
    return state


def bounding_box(live: Iterable[Cell]) -> tuple[int, int, int, int] | None:
    state = tuple(live)
    if not state:
        return None
    xs = [x for x, _ in state]
    ys = [y for _, y in state]
    return min(xs), min(ys), max(xs), max(ys)


def coordinate_bytes(live: Iterable[Cell]) -> bytes:
    """Canonical exact-coordinate representation for hashing."""
    return "".join(
        f"{x},{y}\n" for x, y in sorted(live, key=lambda point: (point[1], point[0]))
    ).encode("ascii")


def coordinate_sha256(live: Iterable[Cell]) -> str:
    return hashlib.sha256(coordinate_bytes(live)).hexdigest()


def state_summary(live: Iterable[Cell]) -> dict[str, object]:
    state = frozenset(live)
    return {
        "population": len(state),
        "bounding_box": bounding_box(state),
        "coordinate_sha256": coordinate_sha256(state),
    }


def _runs(row: str) -> str:
    if not row:
        return ""
    out: list[str] = []
    start = 0
    while start < len(row):
        end = start + 1
        while end < len(row) and row[end] == row[start]:
            end += 1
        length = end - start
        out.append((str(length) if length > 1 else "") + row[start])
        start = end
    return "".join(out)


def to_rle(live: Iterable[Cell], rule: str = "B3/S23") -> str:
    """Write RLE translated so the live-cell bounding box starts at (0,0)."""
    state = frozenset(live)
    box = bounding_box(state)
    if box is None:
        return f"x = 0, y = 0, rule = {normalise_rule(rule)}\n!\n"

    min_x, min_y, max_x, max_y = box
    width = max_x - min_x + 1
    height = max_y - min_y + 1
    translated = {(x - min_x, y - min_y) for x, y in state}
    rows: list[str] = []
    for y in range(height):
        raw = "".join("o" if (x, y) in translated else "b" for x in range(width))
        rows.append(_runs(raw.rstrip("b")))
    while rows and not rows[-1]:
        rows.pop()
    body = "$".join(rows) + "!"
    return f"x = {width}, y = {height}, rule = {normalise_rule(rule)}\n{body}\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="input RLE")
    parser.add_argument("--gens", type=int, default=0, help="generations to advance")
    parser.add_argument("--output", type=Path, help="optional output RLE")
    parser.add_argument("--json", type=Path, help="optional summary JSON")
    args = parser.parse_args()

    pattern = read_rle(args.input)
    result = advance(pattern.live, args.gens)
    summary: dict[str, object] = {
        "input": str(args.input),
        "generations": args.gens,
        **state_summary(result),
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(to_rle(result), encoding="utf-8")
        summary["output"] = str(args.output)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
