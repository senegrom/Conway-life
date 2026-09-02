#!/usr/bin/env python3
"""Boundary-layer analysis of the padding flip point (Salo-Torma, Q28820954).

Layers of a preimage patch, from a rectangular pattern P outward:
  d0 = P's own boundary layer, d1 = ring at distance 1, d2 = distance 2,
  d3 = distance 3. The image of P depends on layers <= 1 only; the image of
ring R1 (distance 1) depends on d0,d1,d2; the image of ring R2 on d1,d2,d3.
So, given a pad^1 preimage, extending it to a pad^2 preimage is a purely
one-dimensional problem along the boundary: keep (d0,d1), re-choose d2 and
choose d3 so that R1 stays dead and R2 becomes dead.

A boundary pair (d0,d1) on a straight segment is
  level-1 deadly : no d2 makes R1 dead          (mechanism behind f = 1)
  level-2 deadly : some d2 makes R1 dead, but no (d2,d3) makes R1 and R2
                   both dead                     (the ONLY mechanism for f = 2)

If no level-2 deadly boundary exists at all, every pad^1 preimage extends
and the padding constant is exactly 1. This script brute-forces straight
free-end segments of length L (constraints imposed on cells 1..L-2, whose
neighbourhoods lie inside the segment), which is sound as an obstruction
detector: a deadly segment embedded anywhere in a boundary blocks extension.
"""

from __future__ import annotations

import argparse
import itertools
import sys


def life(centre: int, count: int) -> int:
    return 1 if count == 3 or (count == 2 and centre == 1) else 0


def bit(v: int, i: int) -> int:
    return (v >> i) & 1


def win(v: int, i: int) -> int:
    """Number of live cells among positions i-1, i, i+1 of row v (i >= 1)."""
    return bit(v, i - 1) + bit(v, i) + bit(v, i + 1)


def r1_dead(d0: int, d1: int, d2: int, x: int) -> bool:
    count = win(d0, x) + bit(d1, x - 1) + bit(d1, x + 1) + win(d2, x)
    return life(bit(d1, x), count) == 0


def r2_dead(d1: int, d2: int, d3: int, x: int) -> bool:
    count = win(d1, x) + bit(d2, x - 1) + bit(d2, x + 1) + win(d3, x)
    return life(bit(d2, x), count) == 0


def classify(L: int):
    """Return (level1_deadly, level2_deadly) lists of (d0, d1) for segment L."""
    xs = range(1, L - 1)
    rows = range(1 << L)
    lvl1, lvl2 = [], []
    for d0 in rows:
        for d1 in rows:
            r1_solutions = [d2 for d2 in rows if all(r1_dead(d0, d1, d2, x) for x in xs)]
            if not r1_solutions:
                lvl1.append((d0, d1))
                continue
            extendable = False
            for d2 in r1_solutions:
                if any(all(r2_dead(d1, d2, d3, x) for x in xs) for d3 in rows):
                    extendable = True
                    break
            if not extendable:
                lvl2.append((d0, d1))
    return lvl1, lvl2


def show(L: int, d0: int, d1: int) -> str:
    f = lambda v: "".join(str(bit(v, i)) for i in range(L))
    return f"d0={f(d0)} d1={f(d1)}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min", type=int, default=4)
    ap.add_argument("--max", type=int, default=8)
    ap.add_argument("--examples", type=int, default=5)
    a = ap.parse_args()
    for L in range(a.min, a.max + 1):
        lvl1, lvl2 = classify(L)
        total = 1 << (2 * L)
        print(f"L={L}: {total} boundary pairs; level-1 deadly {len(lvl1)}; "
              f"level-2 deadly {len(lvl2)}", flush=True)
        for d0, d1 in lvl2[: a.examples]:
            print("   level-2:", show(L, d0, d1), flush=True)
        if not lvl2 and lvl1:
            print("   (level-1 deadly example:", show(L, *lvl1[0]) + ")", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
