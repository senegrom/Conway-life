#!/usr/bin/env python3
"""Forcing-strip search for f = 2 as a dual 2QBF (CAQE).

A level-2 deadly boundary word W = (d0, d1) of length w (see
data/discoveries/deadly-boundary-words.txt) is the only mechanism for
f = 2. A pattern has f = 2 iff EVERY pad^1 preimage carries such a word.
This instance asks whether a top strip S (height h, width w) can force it:

    forall T0 [a preimage patch whose top two layers are W]
    exists T, d2', d3 :  img(T) = img(T0) on the strip
                         and R1 dead, R2 dead at x = 1..w-2

TRUE  (CAQE exit 10): every strip that admits a W-boundary preimage also
      admits an extendable preimage -> no forcing strip of this shape.
FALSE (exit 20): the falsifying T0 gives S = img(T0), a strip all of whose
      preimages have non-extendable boundaries -> an f = 2 core (complete
      it to a pattern with pad^1 satisfiable and f = 2 follows).

Layers: T0/T rows y = -1..h (row -1 = d1, row 0 = d0 = strip's own top
row layer), columns x = -1..w; d2' at row -2, d3 at row -3, columns 0..w-1.
Constants (W) are substituted, not quantified.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goe4_qbf import _ON_COVER, _OFF_COVER  # noqa: E402

OFFS = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]  # bit k of covers


class Gen:
    def __init__(self):
        self.n = 0
        self.clauses: list[list[int]] = []

    def fresh(self) -> int:
        self.n += 1
        return self.n

    def add(self, lits):
        out = []
        for l in lits:
            if l is True:
                return
            if l is False:
                continue
            out.append(l)
        self.clauses.append(out)


def const(v: int):
    return ("const", v)


def lit(cell, positive: bool):
    if isinstance(cell, tuple):
        return (cell[1] == 1) == positive
    return cell if positive else -cell


def cover_clauses(g: Gen, nbhd, tail=None, force_dead=False):
    """nbhd: 9 cells (vars or consts) in OFFS order.
    tail: image var t -> add t <-> Life(nbhd).  force_dead: add Life(nbhd)=0."""
    def term(value, mask, extra):
        lits = []
        for k in range(9):
            if mask & (1 << k):
                continue
            lits.append(lit(nbhd[k], positive=not (value & (1 << k))))
        g.add(lits + extra)
    if force_dead:
        for value, mask in _ON_COVER:
            term(value, mask, [])
    if tail is not None:
        for value, mask in _ON_COVER:
            term(value, mask, [tail])
        for value, mask in _OFF_COVER:
            term(value, mask, [-tail])


def generate(d0: str, d1: str, h: int):
    w = len(d0)
    assert len(d1) == w
    g = Gen()
    t0, univ = {}, []
    for y in range(-1, h + 1):
        for x in range(-1, w + 1):
            if y == -1 and 0 <= x < w:
                t0[(y, x)] = const(int(d1[x]))
            elif y == 0 and 0 <= x < w:
                t0[(y, x)] = const(int(d0[x]))
            else:
                v = g.fresh(); t0[(y, x)] = v; univ.append(v)
    exist, t = [], {}
    for y in range(-1, h + 1):
        for x in range(-1, w + 1):
            v = g.fresh(); t[(y, x)] = v; exist.append(v)
    d2 = {x: g.fresh() for x in range(w)}
    d3 = {x: g.fresh() for x in range(w)}
    exist += list(d2.values()) + list(d3.values())
    for y in range(h):
        for x in range(w):
            i0 = g.fresh(); i1 = g.fresh(); exist += [i0, i1]
            cover_clauses(g, [t0[(y + dy, x + dx)] for dy, dx in OFFS], tail=i0)
            cover_clauses(g, [t[(y + dy, x + dx)] for dy, dx in OFFS], tail=i1)
            g.add([-i0, i1]); g.add([i0, -i1])
    for x in range(1, w - 1):  # R1 dead at row -1
        nb = [d2[x + dx] if -1 + dy == -2 else t[(-1 + dy, x + dx)] for dy, dx in OFFS]
        cover_clauses(g, nb, force_dead=True)
    for x in range(1, w - 1):  # R2 dead at row -2
        nb = []
        for dy, dx in OFFS:
            yy, xx = -2 + dy, x + dx
            nb.append(d3[xx] if yy == -3 else d2[xx] if yy == -2 else t[(yy, xx)])
        cover_clauses(g, nb, force_dead=True)
    lines = [f"p cnf {g.n} {len(g.clauses)}",
             "a " + " ".join(map(str, univ)) + " 0",
             "e " + " ".join(map(str, exist)) + " 0"]
    lines += [" ".join(map(str, c)) + " 0" for c in g.clauses]
    return "\n".join(lines) + "\n", {"t0": t0, "w": w, "h": h}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--d0", required=True)
    ap.add_argument("--d1", required=True)
    ap.add_argument("--height", type=int, default=2)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--caqe", type=Path)
    ap.add_argument("--timeout", type=int, default=3600)
    a = ap.parse_args()
    text, meta = generate(a.d0, a.d1, a.height)
    a.out.write_text(text, encoding="ascii", newline="\n")
    print(f"wrote {a.out}: {text.splitlines()[0]}, universal bits "
          f"{len(text.splitlines()[1].split()) - 2}", flush=True)
    if not a.caqe:
        return 0
    try:
        r = subprocess.run([str(a.caqe), "--qdo", str(a.out)], capture_output=True,
                           text=True, timeout=a.timeout)
    except subprocess.TimeoutExpired:
        print("CAQE TIMEOUT", flush=True)
        return 3
    verdict = {10: "TRUE (no forcing strip of this shape)",
               20: "FALSE (FORCING STRIP FOUND)"}.get(r.returncode, "?")
    print(f"CAQE exit {r.returncode}: {verdict}", flush=True)
    if r.returncode == 20:
        vals = {}
        for line in r.stdout.splitlines():
            if line.startswith("V"):
                for tok in line.split()[1:]:
                    v = int(tok)
                    if v:
                        vals[abs(v)] = 1 if v > 0 else 0
        t0, w, h = meta["t0"], meta["w"], meta["h"]
        print("falsifying T0 (rows -1..h, cols -1..w):")
        for y in range(-1, h + 1):
            row = "".join(str(t0[(y, x)][1]) if isinstance(t0[(y, x)], tuple)
                          else str(vals.get(t0[(y, x)], "?")) for x in range(-1, w + 1))
            print("  " + row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
