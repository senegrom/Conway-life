#!/usr/bin/env python3
"""Generate the stream-synthetic antiparallel glider-tape workload.

Lanes run along the main (southeast) diagonal. Lane j is offset j*spacing
cells in the perpendicular direction (1,-1); within a lane, gliders are
placed every `pitch` cells along the diagonal (1,1). Even lanes carry
southeast-going gliders, odd lanes carry northwest-going gliders (the
180-degree rotation), giving separated antiparallel streams — StreamLife's
design case. With perpendicular lane separation >= 6 the streams can never
interact, so for any generation count the population is exactly
5 * lanes * gliders_per_lane and every engine must agree bit-for-bit.

Deterministic; parameters pin the workload. Output is a normalised RLE via
the trusted reference implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_life as life

# Southeast-going glider, from the pinned benchmarks/patterns/glider.rle
# (advance by 4 = shift (+1,+1), verified by the repository test suite).
SE_GLIDER = [(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)]


def rot180(cells: list[tuple[int, int]]) -> list[tuple[int, int]]:
    max_x = max(x for x, _ in cells)
    max_y = max(y for _, y in cells)
    return [(max_x - x, max_y - y) for x, y in cells]


NW_GLIDER = rot180(SE_GLIDER)


MASK64 = (1 << 64) - 1


def splitmix64(state: int) -> tuple[int, int]:
    state = (state + 0x9E3779B97F4A7C15) & MASK64
    z = state
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
    return state, z ^ (z >> 31)


def build(
    lanes: int, per_lane: int, pitch: int, spacing: int, jitter: int, seed: int
) -> frozenset[tuple[int, int]]:
    """jitter > 0 adds a seeded aperiodic offset in [0, jitter) (multiples of 4,
    preserving glider phase) to each inter-glider gap, destroying the spatial
    periodicity that makes the tape HashLife-trivial. Streams still cannot
    interact: gaps only grow."""
    live: set[tuple[int, int]] = set()
    state = seed & MASK64
    for j in range(lanes):
        base = SE_GLIDER if j % 2 == 0 else NW_GLIDER
        ox, oy = j * spacing, -j * spacing
        pos = 0
        for _ in range(per_lane):
            dx, dy = ox + pos, oy + pos
            for x, y in base:
                cell = (x + dx, y + dy)
                if cell in live:
                    raise SystemExit("overlap — bad parameters")
                live.add(cell)
            step = pitch
            if jitter > 0:
                state, draw = splitmix64(state)
                step += 4 * (draw % (jitter // 4 + 1))
            pos += step
    return frozenset(live)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lanes", type=int, default=16)
    parser.add_argument("--per-lane", type=int, default=64)
    parser.add_argument("--pitch", type=int, default=64, help="cells between gliders along a lane")
    parser.add_argument("--spacing", type=int, default=32, help="perpendicular cells between lanes")
    parser.add_argument("--jitter", type=int, default=0, help="max aperiodic extra gap (multiple of 4)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.spacing < 8 or args.pitch < 16:
        raise SystemExit("keep spacing >= 8 and pitch >= 16 so streams cannot interact")

    live = build(args.lanes, args.per_lane, args.pitch, args.spacing, args.jitter, args.seed)
    expected = 5 * args.lanes * args.per_lane
    if len(live) != expected:
        raise SystemExit(f"population {len(live)} != {expected}")

    # Sanity: 4 generations must be an exact per-lane translation (all gliders
    # advance one diagonal step; SE lanes by (+1,+1), NW lanes by (-1,-1)).
    stepped = life.advance(live, 4)
    if len(stepped) != expected:
        raise SystemExit("gliders interacted within 4 generations — bad parameters")

    rle = life.to_rle(live)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(rle, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "out": str(args.out),
                "lanes": args.lanes,
                "per_lane": args.per_lane,
                "pitch": args.pitch,
                "spacing": args.spacing,
                "jitter": args.jitter,
                "seed": args.seed,
                "population": expected,
                "bounding_box": life.bounding_box(live),
                "coordinate_sha256": life.coordinate_sha256(live),
                "rle_sha256": hashlib.sha256(
                    args.out.read_bytes()
                ).hexdigest(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
