#!/usr/bin/env python3
"""Transfer-matrix version of boundary_deadly.py (numpy), for segments up
to L ~ 13. Same semantics: straight free-end segment of length L, layers
d0,d1 given, d2,d3 free; constraints R1-dead and R2-dead imposed at cells
x = 1..L-2.

DP state at position x: (d2[x-1], d2[x], d3[x-1], d3[x]) -> 16 states.
Reachable-state sets are 16-bit masks; a transition table maps
(d0 window, d1 window, mask) -> next mask, and the DP is vectorised over
all d1 for each d0. Joint DP (R1 and R2 dead) and R1-only DP (ignore d3)
run side by side.

  level-1 deadly : R1-only DP unsat
  level-2 deadly : R1-only DP sat and joint DP unsat
"""

from __future__ import annotations

import argparse
import itertools
import sys

import numpy as np


def life(c: int, n: int) -> int:
    return 1 if n == 3 or (n == 2 and c == 1) else 0


def build_tables():
    """Per (d0win, d1win) in 0..63: joint[mask]->mask and r1[mask]->mask.

    Windows are 3-bit values with bit0 = x-1, bit1 = x, bit2 = x+1.
    State s = d2[x-1] | d2[x]<<1 | d3[x-1]<<2 | d3[x]<<3.
    Choosing (d2[x+1], d3[x+1]) gives next state
        s' = d2[x] | d2[x+1]<<1 | d3[x]<<2 | d3[x+1]<<3.
    """
    joint = np.zeros((64, 1 << 16), dtype=np.uint16)
    r1 = np.zeros((64, 1 << 16), dtype=np.uint16)
    # per (w, state) -> next-state mask
    joint_s = np.zeros((64, 16), dtype=np.uint16)
    r1_s = np.zeros((64, 16), dtype=np.uint16)
    for w in range(64):
        d0w, d1w = w & 7, w >> 3
        d0c = bin(d0w).count("1")
        d1m = (d1w >> 1) & 1
        d1lat = (d1w & 1) + ((d1w >> 2) & 1)
        d1c = d0c  # placeholder, recomputed below
        for s in range(16):
            a, b, c, d = s & 1, (s >> 1) & 1, (s >> 2) & 1, (s >> 3) & 1
            jm = 0
            rm = 0
            for e, f in itertools.product((0, 1), repeat=2):
                # e = d2[x+1], f = d3[x+1]
                d2win = a + b + e
                r1_ok = life(d1m, d0c + d1lat + d2win) == 0
                d3win = c + d + f
                d1win_cnt = bin(d1w).count("1")
                r2_ok = life(b, d1win_cnt + a + e + d3win) == 0
                ns = b | (e << 1) | (d << 2) | (f << 3)
                if r1_ok:
                    rm |= 1 << ns
                    if r2_ok:
                        jm |= 1 << ns
            joint_s[w, s] = jm
            r1_s[w, s] = rm
    # expand to mask -> mask (OR over set bits)
    masks = np.arange(1 << 16, dtype=np.uint32)
    for w in range(64):
        jt = np.zeros(1 << 16, dtype=np.uint32)
        rt = np.zeros(1 << 16, dtype=np.uint32)
        for s in range(16):
            sel = (masks >> s) & 1 == 1
            jt[sel] |= int(joint_s[w, s])
            rt[sel] |= int(r1_s[w, s])
        joint[w] = jt.astype(np.uint16)
        r1[w] = rt.astype(np.uint16)
    return joint, r1


def run(L: int, joint, r1, examples: int):
    n = 1 << L
    d1 = np.arange(n, dtype=np.uint32)
    lvl1 = lvl2 = 0
    shown = 0
    ex = []
    for d0 in range(n):
        jm = np.full(n, 0xFFFF, dtype=np.uint16)
        rm = np.full(n, 0xFFFF, dtype=np.uint16)
        for x in range(1, L - 1):
            d0w = (d0 >> (x - 1)) & 7
            d1w = (d1 >> (x - 1)) & 7
            w = d0w | (d1w << 3)
            jm = joint[w, jm]
            rm = r1[w, rm]
        r1sat = rm != 0
        jsat = jm != 0
        l1 = ~r1sat
        l2 = r1sat & ~jsat
        lvl1 += int(l1.sum())
        c2 = int(l2.sum())
        lvl2 += c2
        if c2 and len(ex) < examples:
            for d1v in np.nonzero(l2)[0][: examples - len(ex)]:
                ex.append((d0, int(d1v)))
    return lvl1, lvl2, ex


def fmt(L, v):
    return "".join(str((v >> i) & 1) for i in range(L))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min", type=int, default=6)
    ap.add_argument("--max", type=int, default=11)
    ap.add_argument("--examples", type=int, default=8)
    a = ap.parse_args()
    joint, r1 = build_tables()
    for L in range(a.min, a.max + 1):
        lvl1, lvl2, ex = run(L, joint, r1, a.examples)
        print(f"L={L}: pairs {1 << (2 * L)}; level-1 deadly {lvl1}; level-2 deadly {lvl2}", flush=True)
        for d0, d1 in ex:
            print(f"   level-2: d0={fmt(L, d0)} d1={fmt(L, d1)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
