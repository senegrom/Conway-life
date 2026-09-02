#!/usr/bin/env python3
"""Complete-ring deadliness test on small rectangles (corners + cyclic
closure included), via incremental SAT.

For a rectangle B = n x m, layers by Chebyshev distance: d0 = boundary
cells of B, d1 = distance 1, d2 = distance 2, d3 = distance 3. Given an
assignment of (d0, d1) — the two outer layers of a hypothetical pad^1
preimage — ask:
    R1-sat : exists d2 with every distance-1 cell's image dead
    joint  : exists (d2, d3) with distance-1 AND distance-2 images dead
A (d0,d1) that is R1-sat but not joint-sat is a level-2 deadly ring: the
only possible mechanism for a pattern with flip point f = 2. If no such
ring exists for a rectangle size, no pattern of that size has f = 2.

Exhaustive over all 2^(|d0|+|d1|) assignments, or random sampling.
"""

from __future__ import annotations

import argparse
import itertools
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preimage_sat import life_out  # noqa: E402

NEIGH = [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)]


def dist(x: int, y: int, n: int, m: int) -> int:
    return max(-x, x - (n - 1), -y, y - (m - 1), 0)


def build(n: int, m: int):
    from pysat.solvers import Solver

    cells = {}
    layer = {}
    for x in range(-3, n + 3):
        for y in range(-3, m + 3):
            d = dist(x, y, n, m)
            if d > 3:
                continue
            if d == 0 and 0 < x < n - 1 and 0 < y < m - 1:
                continue  # interior of B: irrelevant to rings 1, 2
            cells[(x, y)] = len(cells) + 1
            layer[(x, y)] = d
    live_assign = [a for a in itertools.product((0, 1), repeat=9) if life_out(a) == 1]

    def dead_clauses(cx, cy):
        vs = [cells[(cx + dr, cy + dc)] for dr, dc in NEIGH]
        return [[-v if bit else v for v, bit in zip(vs, a)] for a in live_assign]

    r1_cl, joint_cl = [], []
    for (x, y), d in layer.items():
        if d == 1:
            cl = dead_clauses(x, y)
            r1_cl += cl
            joint_cl += cl
        elif d == 2:
            joint_cl += dead_clauses(x, y)
    given = [c for c, d in layer.items() if d in (0, 1)]
    return (Solver(name="g3", bootstrap_with=r1_cl),
            Solver(name="g3", bootstrap_with=joint_cl),
            cells, layer, given)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--m", type=int, required=True)
    ap.add_argument("--samples", type=int, default=0, help="0 = exhaustive")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--report-every", type=float, default=60.0)
    a = ap.parse_args()
    r1s, js, cells, layer, given = build(a.n, a.m)
    k = len(given)
    total = a.samples if a.samples else (1 << k)
    print(f"ring test {a.n}x{a.m}: {k} given cells (d0+d1), "
          f"{'sampling ' + str(a.samples) if a.samples else 'exhaustive ' + str(total)}",
          flush=True)
    rng = random.Random(a.seed)
    t0 = time.perf_counter()
    last = t0
    lvl1 = lvl2 = 0
    for i in range(total):
        bits = rng.getrandbits(k) if a.samples else i
        assum = [cells[c] if (bits >> j) & 1 else -cells[c] for j, c in enumerate(given)]
        if not r1s.solve(assumptions=assum):
            lvl1 += 1
        elif not js.solve(assumptions=assum):
            lvl2 += 1
            print(f"*** LEVEL-2 DEADLY RING bits={bits}", flush=True)
            for y in range(-1, a.m + 1):
                row = ""
                for x in range(-1, a.n + 1):
                    c = (x, y)
                    row += str((bits >> given.index(c)) & 1) if c in given else "."
                print("   " + row, flush=True)
        now = time.perf_counter()
        if now - last > a.report_every:
            print(f"  {i + 1}/{total}, level-1 {lvl1}, level-2 {lvl2}, "
                  f"{(i + 1) / (now - t0):.0f}/s", flush=True)
            last = now
    print(f"DONE ring {a.n}x{a.m}: checked {total}, level-1 deadly {lvl1}, "
          f"level-2 deadly {lvl2}, {time.perf_counter() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
