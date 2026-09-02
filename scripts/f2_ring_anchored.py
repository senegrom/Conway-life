#!/usr/bin/env python3
"""Deadly-word-anchored ring-extension search for f = 2.

Necessary condition for f(P') = 2: some pad^1 preimage of P' carries a
level-2 deadly boundary word; for a D4-symmetric core the side can be taken
as the top. So, for a witness core P (13x13, bare SAT / pad^1 UNSAT) and each
deadly 15-word W = (d0, d1): enumerate the distinct ring images r of pad^1
preimage patches X of P' = P (+) r whose top boundary layers equal W
(d0 = X on P''s top row, d1 = X on the ring-1 row above), then test
pad^2(P') for each distinct r. Complete for the necessary condition within
the ring-extension family, per (core, word).

Coordinates: pad^1 window (k+4)^2, preimage patch X (k+6)^2; P' cell (py,px)
is patch (py+2, px+2); ring-1 top row is patch row 1; d0[i] = X[2][2+i],
d1[i] = X[1][2+i], i = 0..14.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preimage_sat as ps
from padding_flip import pad_window
from ring_orphan_search import WindowTemplate
from goe4_qbf import _ON_COVER, _OFF_COVER
from f2_ring_extend import harvest_cores

OFFS = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
BUILD = Path(r"D:\Programs\life-research\build")


def build_base(core, k: int):
    """Clauses for: image = core on the core cells, ring-1 dead, ring cells
    of P' given image variables. Returns (clauses, nvars, ring_img dict)."""
    n = k + 2; W = n + 2; X = W + 2
    nv = 0; xv = {}
    for y in range(X):
        for x in range(X):
            nv += 1; xv[(y, x)] = nv
    clauses = []

    def term(nb, value, mask, extra):
        lits = []
        for kk in range(9):
            if mask & (1 << kk):
                continue
            v = nb[kk]
            lits.append(-v if (value >> kk) & 1 else v)
        clauses.append(lits + extra)

    ring_img = {}
    for y in range(W):
        for x in range(W):
            nb = [xv[(y + 1 + dy, x + 1 + dx)] for dy, dx in OFFS]
            if y in (0, W - 1) or x in (0, W - 1):
                for value, mask in _ON_COVER:
                    term(nb, value, mask, [])
            else:
                py, px = y - 1, x - 1
                if py in (0, n - 1) or px in (0, n - 1):
                    nv += 1; t = nv; ring_img[(py, px)] = t
                    for value, mask in _ON_COVER:
                        term(nb, value, mask, [t])
                    for value, mask in _OFF_COVER:
                        term(nb, value, mask, [-t])
                else:
                    if core[py - 1][px - 1]:
                        for value, mask in _OFF_COVER:
                            term(nb, value, mask, [])
                    else:
                        for value, mask in _ON_COVER:
                            term(nb, value, mask, [])
    return clauses, nv, ring_img, xv


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--core", type=int, default=13)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int)
    ap.add_argument("--words", type=Path, default=BUILD / "deadly15.txt")
    ap.add_argument("--cap", type=int, default=5000, help="max rings per (core, word)")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    from pysat.solvers import Solver
    k = a.core; n = k + 2
    cores = [c for c in harvest_cores(k) if c[0].startswith("f1")]
    end = a.end if a.end is not None else len(cores)
    words = [tuple(line.split()) for line in a.words.read_text().split("\n") if line.strip()]
    ring2 = WindowTemplate(n + 4, n + 4, 2)
    cells = [(i, j) for i in range(n) for j in range(n)]
    r2v = {c: ring2.w_var[(c[0] + 2, c[1] + 2)] for c in cells}
    print(f"anchored ring search: {len(cores)} witness cores, cores [{a.start},{end}), "
          f"{len(words)} deadly 15-words, cap {a.cap}/(core,word)", flush=True)
    t0 = time.perf_counter()
    tot_rings = tot_feasible = f2 = 0
    for ci in range(a.start, end):
        label, core = cores[ci]
        clauses, nv, ring_img, xv = build_base(core, k)
        base = [[0] * n for _ in range(n)]
        for i in range(k):
            for j in range(k):
                base[i + 1][j + 1] = core[i][j]
        rvars = list(ring_img.items())
        seen_r = set()
        feasible_words = 0
        tc = time.perf_counter()
        with Solver(name="g3", bootstrap_with=clauses) as s:
            for d0, d1 in words:
                assum = []
                for i in range(15):
                    v0 = xv[(2, 2 + i)]; v1 = xv[(1, 2 + i)]
                    assum.append(v0 if d0[i] == "1" else -v0)
                    assum.append(v1 if d1[i] == "1" else -v1)
                blocks = []
                cnt = 0
                while cnt < a.cap and s.solve(assumptions=assum + blocks):
                    m = set(l for l in s.get_model() if l > 0)
                    rbits = tuple(1 if v in m else 0 for _, v in rvars)
                    cnt += 1
                    # block this ring for the rest of this word (via an activation trick:
                    # add as a permanent clause guarded by nothing -> blocks for all words too,
                    # which is fine: a ring already tested need not be re-tested)
                    s.add_clause([-v if v in m else v for _, v in rvars])
                    if rbits in seen_r:
                        continue
                    seen_r.add(rbits)
                    raster = [row[:] for row in base]
                    for ((i, j), _), b in zip(rvars, rbits):
                        raster[i][j] = b
                    a2 = [r2v[c] if raster[c[0]][c[1]] else -r2v[c] for c in cells]
                    if ring2.has_preimage(a2):
                        continue
                    slow1, _ = ps.check_window(pad_window(raster, 1))
                    slow2, _ = ps.check_window(pad_window(raster, 2))
                    rows = ["".join(map(str, row)) for row in raster]
                    if slow1 and not slow2:
                        f2 += 1
                        print(f"*** F2-WITNESS (slow-verified) core={label} word={d0}/{d1} "
                              f"pop={sum(map(sum, raster))} — PADDING CONSTANT >= 2", flush=True)
                    else:
                        print(f"MISMATCH core={label} word={d0}/{d1}: slow pad1={slow1} pad2={slow2}", flush=True)
                    for row in rows:
                        print(row, flush=True)
                if cnt:
                    feasible_words += 1
                tot_rings += cnt
        tot_feasible += feasible_words
        print(f"  core {ci} {label}: {feasible_words}/{len(words)} words feasible, "
              f"{len(seen_r)} distinct rings, {time.perf_counter() - tc:.0f}s, f2 so far {f2}", flush=True)
    print(f"DONE anchored {k} [{a.start},{end}): rings {tot_rings}, feasible (core,word) {tot_feasible}, "
          f"f2={f2}, {time.perf_counter() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
