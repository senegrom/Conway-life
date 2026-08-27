#!/usr/bin/env python3
"""Incremental search for dead-ringed orphans / padding-flip witnesses.

Hunts K x K cores P (symmetric under a chosen group) such that the
(K+2) x (K+2) window pad^1(P) — P surrounded by one specified dead ring —
is an ORPHAN. Each find is classified:

    bare P preimageable  -> f(P) = 1 witness for Salo's padding question
    bare P also an orphan -> a new small orphan with an all-dead border ring

Speed comes from two persistent incremental SAT solvers (pysat) built once
per shape: window cell values are assumption literals, so each candidate is
one solver.solve(assumptions=...) call instead of a fresh CNF build. The
encoding is the same exhaustively validated one as scripts/preimage_sat.py
(512 blocked neighbourhood assignments per cell, with the cell value as a
literal instead of a constant).

Symmetric patterns are enumerated as subsets of cell orbits (D4 or C4), so
each candidate is generated exactly once. Ranges allow parallel workers.
"""

from __future__ import annotations

import argparse
import itertools
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preimage_sat import life_out  # noqa: E402

NEIGH = [(dr, dc) for dr in (0, 1, 2) for dc in (0, 1, 2)]


class WindowTemplate:
    """Incremental preimage checker for an H x W window whose cells are
    assumption variables (ring cells may be fixed dead)."""

    def __init__(self, height: int, width: int, dead_ring, solver_name: str = "g3"):
        from pysat.solvers import Solver

        ring = int(dead_ring)  # ring width in cells; bool True == 1
        self.h, self.w = height, width
        ph, pw = height + 2, width + 2
        next_var = 1
        self.x_var = {}
        for r in range(ph):
            for c in range(pw):
                self.x_var[(r, c)] = next_var
                next_var += 1
        self.w_var = {}
        for i in range(height):
            for j in range(width):
                self.w_var[(i, j)] = next_var
                next_var += 1

        clauses = []
        for i in range(height):
            for j in range(width):
                on_ring = (
                    i < ring or j < ring or i >= height - ring or j >= width - ring
                )
                cell_vars = [self.x_var[(i + dr, j + dc)] for dr, dc in NEIGH]
                v = self.w_var[(i, j)]
                for assignment in itertools.product((0, 1), repeat=9):
                    base = [-x if bit else x for x, bit in zip(cell_vars, assignment)]
                    out = life_out(assignment)
                    if on_ring:
                        if out == 1:
                            clauses.append(base)  # ring must stay dead
                    else:
                        clauses.append(base + ([v] if out == 1 else [-v]))
        self.solver = Solver(name=solver_name, bootstrap_with=clauses)

    def interior_cells(self, dead_ring: bool):
        if not dead_ring:
            return [(i, j) for i in range(self.h) for j in range(self.w)]
        return [
            (i, j)
            for i in range(1, self.h - 1)
            for j in range(1, self.w - 1)
        ]

    def has_preimage(self, assumptions: list[int]) -> bool:
        return self.solver.solve(assumptions=assumptions)


def cell_orbits(k: int, group: str) -> list[list[tuple[int, int]]]:
    def images(i, j):
        rots = [(i, j), (j, k - 1 - i), (k - 1 - i, k - 1 - j), (k - 1 - j, i)]
        if group == "d4":
            rots += [(j, i), (i, k - 1 - j), (k - 1 - j, k - 1 - i), (k - 1 - i, j)]
        return frozenset(rots)

    seen, orbits = set(), []
    for i in range(k):
        for j in range(k):
            o = images(i, j)
            if o not in seen:
                seen.add(o)
                orbits.append(sorted(o))
    return orbits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=int, required=True, help="core size K")
    parser.add_argument("--group", choices=["d4", "c4"], required=True)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, help="exclusive; default 2^orbits")
    parser.add_argument("--report-every", type=float, default=60.0)
    args = parser.parse_args()

    k = args.core
    orbits = cell_orbits(k, args.group)
    n = len(orbits)
    end = args.end if args.end is not None else (1 << n)
    print(f"core {k}x{k}, group {args.group}: {n} orbits; range [{args.start}, {end})", flush=True)

    padded = WindowTemplate(k + 2, k + 2, dead_ring=True)
    bare = WindowTemplate(k, k, dead_ring=False)

    # Map orbit index -> assumption literals in each template. In the padded
    # template the core occupies the interior (offset +1).
    pad_orbit_vars = [[padded.w_var[(i + 1, j + 1)] for i, j in o] for o in orbits]
    bare_orbit_vars = [[bare.w_var[(i, j)] for i, j in o] for o in orbits]
    all_pad_vars = [v for vs in pad_orbit_vars for v in vs]
    all_bare_vars = [v for vs in bare_orbit_vars for v in vs]

    t0 = time.perf_counter()
    last = t0
    finds = 0
    for bits in range(args.start, end):
        pos_pad, pos_bare = set(), set()
        for idx in range(n):
            if bits >> idx & 1:
                pos_pad.update(pad_orbit_vars[idx])
                pos_bare.update(bare_orbit_vars[idx])
        assumptions_pad = [v if v in pos_pad else -v for v in all_pad_vars]
        if padded.has_preimage(assumptions_pad):
            now = time.perf_counter()
            if now - last > args.report_every:
                done = bits - args.start + 1
                rate = done / (now - t0)
                print(f"  {done}/{end - args.start} candidates, {rate:.0f}/s", flush=True)
                last = now
            continue
        finds += 1
        assumptions_bare = [v if v in pos_bare else -v for v in all_bare_vars]
        bare_sat = bare.has_preimage(assumptions_bare)
        kind = "F1-WITNESS" if bare_sat else "DEAD-RINGED-ORPHAN"
        print(f"*** {kind} bits={bits} core={k} group={args.group}", flush=True)
        raster = [[0] * k for _ in range(k)]
        for idx in range(n):
            if bits >> idx & 1:
                for i, j in orbits[idx]:
                    raster[i][j] = 1
        for row in raster:
            print("".join(map(str, row)), flush=True)
    print(
        f"DONE core {k} {args.group} [{args.start},{end}): {finds} finds, "
        f"{time.perf_counter() - t0:.0f}s",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
