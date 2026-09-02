#!/usr/bin/env python3
"""Deadly-word-anchored pruning for a D4 15x15 f = 2 census.

Sound necessary condition (straight-side obstructions, top side WLOG for a
D4-symmetric pattern): if f(P) = 2 then some pad^1 preimage of P has a
level-2 deadly (d0, d1) word along the top, so the top rows of P must be
producible from a preimage patch whose top two layers form a deadly 15-word.

mode pairs : for every palindromic (row0, row1) pair (2^16), decide by one
             incremental SAT call whether some deadly 15-word (d0,d1) with
             free rows e1, e2 below produces row0 and row1. Writes the
             compatible pairs to build/anchored-c2.txt.
Later stages extend to more rows / full patterns.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goe4_qbf import _ON_COVER, _OFF_COVER

OFFS = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
BUILD = Path(r"D:\Programs\life-research\build")
W = 15


def palindromes(width: int):
    half = (width + 1) // 2
    for bits in range(1 << half):
        row = [(bits >> i) & 1 for i in range(half)]
        yield row + row[-2::-1] if width % 2 else row + row[::-1]


class CNF:
    def __init__(self):
        self.n = 0; self.cl = []
    def var(self):
        self.n += 1; return self.n
    def term(self, nb, value, mask, extra):
        lits = []
        for k in range(9):
            if mask & (1 << k):
                continue
            v = nb[k]; lits.append(-v if (value >> k) & 1 else v)
        self.cl.append(lits + extra)
    def image(self, nb):
        t = self.var()
        for value, mask in _ON_COVER: self.term(nb, value, mask, [t])
        for value, mask in _OFF_COVER: self.term(nb, value, mask, [-t])
        return t


def build_pairs(words):
    """Rows: -1 = d1, 0 = d0, 1 = e1, 2 = e2; cols -1..W. Image vars for
    pattern rows 0 and 1 (cols 0..W-1). Word selectors force (d0,d1)."""
    c = CNF()
    x = {(y, xx): c.var() for y in range(-1, 3) for xx in range(-1, W + 1)}
    img = {}
    for y in (0, 1):
        for xx in range(W):
            img[(y, xx)] = c.image([x[(y + dy, xx + dx)] for dy, dx in OFFS])
    sels = []
    for d0, d1 in words:
        s = c.var(); sels.append(s)
        for i in range(W):
            v0, v1 = x[(0, i)], x[(-1, i)]
            c.cl.append([-s, v0 if d0[i] == "1" else -v0])
            c.cl.append([-s, v1 if d1[i] == "1" else -v1])
    c.cl.append(sels)
    return c, img


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["pairs"])
    ap.add_argument("--words", type=Path, default=BUILD / "deadly15.txt")
    a = ap.parse_args()
    from pysat.solvers import Solver
    words = [tuple(l.split()) for l in a.words.read_text().split("\n") if l.strip()]
    c, img = build_pairs(words)
    t0 = time.perf_counter()
    compatible = []
    rows = list(palindromes(W))
    with Solver(name="g3", bootstrap_with=c.cl) as s:
        for r0 in rows:
            for r1 in rows:
                assum = [img[(0, i)] if r0[i] else -img[(0, i)] for i in range(W)]
                assum += [img[(1, i)] if r1[i] else -img[(1, i)] for i in range(W)]
                if s.solve(assumptions=assum):
                    compatible.append(("".join(map(str, r0)), "".join(map(str, r1))))
    out = BUILD / "anchored-c2.txt"
    out.write_text("\n".join(f"{a} {b}" for a, b in compatible) + "\n")
    print(f"pairs: {len(rows) ** 2} palindromic (row0,row1) pairs, {len(compatible)} compatible "
          f"with a deadly 15-word ({100 * len(compatible) / len(rows) ** 2:.2f}%), "
          f"{time.perf_counter() - t0:.0f}s -> {out}", flush=True)
    from collections import Counter
    print("distinct compatible row0:", len(set(a for a, _ in compatible)),
          " row1:", len(set(b for _, b in compatible)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
