#!/usr/bin/env python3
"""Generate a pinned pseudo-random dense bounded-plane workload as RLE.

The fill is deterministic: one SplitMix64 draw per cell in row-major order
over the fill region; a cell is born iff draw < floor(density_ppm * 2**64 / 10**6).
The identical generator is implemented in adapters/bb-opencl/bb_gol_bench, and
both sides emit a canonical raster digest (SHA-256 over '0'/'1' rows, each
terminated by '\\n', covering the FULL universe) so cross-language agreement is
checked on every run.

The universe is a bounded plane (dead outside). The RLE is written with a
Golly bounded-grid rule suffix (B3/S23:P<W>,<H>) and a #CXRLE Pos line placing
the fill region at the top-left corner of the universe, so Golly simulates
exactly the same universe as the adapter. Universe dimensions must be even.

The OpenCL engine in binary-banter/fast-game-of-life rounds requested
dimensions up; use effective_dims() to obtain dimensions the engine maps to
itself (width % 32 == 0; height a multiple of 736).
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

MASK64 = (1 << 64) - 1

# Compile-time constants of the pinned binary-banter OpenCL build (settings.toml).
WORK_GROUP_SIZE = 256
WORK_PER_THREAD = 3
PADDING_Y = 16


def effective_dims(width: int, height: int) -> tuple[int, int]:
    """Dimensions the binary-banter OpenCL engine actually simulates.

    Width rounds up to a whole number of 32-cell words. Height rounds up to a
    whole number of per-work-group core blocks (simulation rows); rows the
    kernel never writes back are permanently dead and therefore outside the
    universe.
    """
    eff_w = -(-width // 32) * 32
    core = WORK_GROUP_SIZE * WORK_PER_THREAD - 2 * PADDING_Y
    eff_h = -(-height // core) * core
    return eff_w, eff_h


def splitmix64(state: int) -> tuple[int, int]:
    state = (state + 0x9E3779B97F4A7C15) & MASK64
    z = state
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
    return state, z ^ (z >> 31)


def fill_rows(fill_w: int, fill_h: int, density_ppm: int, seed: int) -> list[list[int]]:
    """Live columns per fill row, drawn row-major with one draw per cell."""
    if not 0 <= density_ppm < 1_000_000:
        raise ValueError("density_ppm must be in [0, 1000000)")
    threshold = (density_ppm << 64) // 1_000_000
    state = seed & MASK64
    rows: list[list[int]] = []
    for _ in range(fill_h):
        row: list[int] = []
        for x in range(fill_w):
            state, draw = splitmix64(state)
            if draw < threshold:
                row.append(x)
        rows.append(row)
    return rows


def raster_digest(universe_w: int, universe_h: int, rows: list[list[int]]) -> tuple[str, int]:
    """Canonical digest over the full universe; rows beyond the fill are dead."""
    hasher = hashlib.sha256()
    population = 0
    empty = b"0" * universe_w + b"\n"
    for y in range(universe_h):
        live = rows[y] if y < len(rows) else []
        if not live:
            hasher.update(empty)
            continue
        row = bytearray(empty)
        for x in live:
            row[x] = 0x31
        population += len(live)
        hasher.update(bytes(row))
    return hasher.hexdigest(), population


def rows_to_rle_body(fill_w: int, rows: list[list[int]]) -> str:
    tokens: list[str] = []
    pending_newlines = 0
    for row in rows:
        if not row:
            pending_newlines += 1
            continue
        if tokens:
            n = pending_newlines + 1
            tokens.append("$" if n == 1 else f"{n}$")
        elif pending_newlines:
            tokens.append(f"{pending_newlines}$")
        pending_newlines = 0
        live = set(row)
        x = 0
        width = max(live) + 1
        while x < width:
            start = x
            alive = x in live
            while x < width and (x in live) == alive:
                x += 1
            run = x - start
            tokens.append((str(run) if run > 1 else "") + ("o" if alive else "b"))
    tokens.append("!")

    # Wrap at token boundaries only; a run count must never span lines.
    lines: list[str] = []
    current = ""
    for token in tokens:
        if current and len(current) + len(token) > 70:
            lines.append(current)
            current = ""
        current += token
    lines.append(current)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, required=True, help="fill width")
    parser.add_argument("--height", type=int, required=True, help="fill height")
    parser.add_argument("--density-ppm", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--universe-width", type=int, help="default: effective_dims")
    parser.add_argument("--universe-height", type=int, help="default: effective_dims")
    parser.add_argument("--out", type=Path, required=True, help="output RLE path")
    args = parser.parse_args()

    eff_w, eff_h = effective_dims(args.width, args.height)
    universe_w = args.universe_width if args.universe_width else eff_w
    universe_h = args.universe_height if args.universe_height else eff_h
    if universe_w % 2 or universe_h % 2:
        raise SystemExit("universe dimensions must be even for CXRLE positioning")
    if args.width > universe_w or args.height > universe_h:
        raise SystemExit("fill region exceeds universe")

    rows = fill_rows(args.width, args.height, args.density_ppm, args.seed)
    digest, population = raster_digest(universe_w, universe_h, rows)

    rle = (
        f"#CXRLE Pos={-universe_w // 2},{-universe_h // 2}\n"
        f"#C seeded dense workload: splitmix64 seed={args.seed} density_ppm={args.density_ppm}\n"
        f"#C fill={args.width}x{args.height} universe={universe_w}x{universe_h} bounded plane\n"
        f"x = {args.width}, y = {args.height}, rule = B3/S23:P{universe_w},{universe_h}\n"
        + rows_to_rle_body(args.width, rows)
        + "\n"
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(rle, encoding="utf-8")
    rle_sha256 = hashlib.sha256(rle.encode("utf-8")).hexdigest()

    print(
        json.dumps(
            {
                "out": str(args.out),
                "fill_width": args.width,
                "fill_height": args.height,
                "universe_width": universe_w,
                "universe_height": universe_h,
                "density_ppm": args.density_ppm,
                "seed": args.seed,
                "population": population,
                "input_raster_sha256": digest,
                "rle_sha256": rle_sha256,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
