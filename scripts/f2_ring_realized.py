#!/usr/bin/env python3
"""Complete ring-extension search per core: enumerate EVERY ring r (not just
D4-symmetric ones) such that P' = P (+) r has pad^1(P') satisfiable, by
projected SAT enumeration of the ring image over pad^1 preimage patches;
then test pad^2(P') for each. If the count is finite and small, this decides
"no ring extension of core P has f = 2" exactly.

Encoding: preimage patch X on the (k+6)x(k+6) box around the (k+2)x(k+2)
pattern P'; image constraints: core cells = P (fixed), ring cells = image
variables (Tseitin via ON/OFF covers), next ring (R1 of P') dead. Enumerate
assignments of the ring-image variables with blocking clauses.
"""

from __future__ import annotations

import argparse
import itertools
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


def realized_rings(core, k: int, cap: int, solver_name="g3"):
    """Yield ring rasters r (dict (i,j)->bit over the (k+2)-box ring) with
    pad^1(P (+) r) satisfiable."""
    from pysat.solvers import Solver
    n = k + 2          # pattern P' size
    W = n + 2          # pad^1 window size
    X = W + 2          # preimage patch size
    nv = 0
    xv = {}
    for y in range(X):
        for x in range(X):
            nv += 1; xv[(y, x)] = nv
    clauses = []

    def cover_term(nb, value, mask, extra):
        lits = []
        for kk in range(9):
            if mask & (1 << kk):
                continue
            v = nb[kk]
            lits.append(-v if (value >> kk) & 1 else v)
        clauses.append(lits + extra)

    def nbhd(y, x):  # image cell (y,x) in window coords -> patch coords +1
        return [xv[(y + 1 + dy, x + 1 + dx)] for dy, dx in OFFS]

    ring_img = {}
    for y in range(W):
        for x in range(W):
            nb = nbhd(y, x)
            if y in (0, W - 1) or x in (0, W - 1):
                # R1 of P': must be dead -> not in any ON implicant
                for value, mask in _ON_COVER:
                    cover_term(nb, value, mask, [])
            else:
                py, px = y - 1, x - 1  # coords in P' (n x n)
                if py in (0, n - 1) or px in (0, n - 1):
                    nv += 1; t = nv; ring_img[(py, px)] = t
                    for value, mask in _ON_COVER:
                        cover_term(nb, value, mask, [t])
                    for value, mask in _OFF_COVER:
                        cover_term(nb, value, mask, [-t])
                else:
                    bit = core[py - 1][px - 1]
                    if bit:
                        for value, mask in _OFF_COVER:
                            cover_term(nb, value, mask, [])   # must be alive: not in OFF
                    else:
                        for value, mask in _ON_COVER:
                            cover_term(nb, value, mask, [])
    rvars = list(ring_img.items())
    count = 0
    with Solver(name=solver_name, bootstrap_with=clauses) as s:
        while count < cap and s.solve():
            m = set(l for l in s.get_model() if l > 0)
            r = {c: (1 if v in m else 0) for c, v in rvars}
            yield r
            count += 1
            s.add_clause([-v if v in m else v for _, v in rvars])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--core", type=int, default=13)
    ap.add_argument("--only", choices=["f0", "f1", "all"], default="f1")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int)
    ap.add_argument("--cap", type=int, default=20000, help="max rings per core")
    a = ap.parse_args()
    k = a.core
    cores = harvest_cores(k)
    if a.only != "all":
        cores = [c for c in cores if c[0].startswith(a.only)]
    end = a.end if a.end is not None else len(cores)
    n = k + 2
    ring2 = WindowTemplate(n + 4, n + 4, 2)
    cells = [(i, j) for i in range(n) for j in range(n)]
    r2v = {c: ring2.w_var[(c[0] + 2, c[1] + 2)] for c in cells}
    print(f"realized-ring f2 search: {len(cores)} cores ({a.only}), cores [{a.start},{end}), cap {a.cap}", flush=True)
    t0 = time.perf_counter()
    tot = f2 = 0
    for ci in range(a.start, end):
        label, core = cores[ci]
        base = [[0] * n for _ in range(n)]
        for i in range(k):
            for j in range(k):
                base[i + 1][j + 1] = core[i][j]
        cnt = 0
        tc = time.perf_counter()
        for r in realized_rings(core, k, a.cap):
            cnt += 1
            raster = [row[:] for row in base]
            for (i, j), b in r.items():
                raster[i][j] = b
            a2 = [r2v[c] if raster[c[0]][c[1]] else -r2v[c] for c in cells]
            if ring2.has_preimage(a2):
                continue
            slow1, _ = ps.check_window(pad_window(raster, 1))
            slow2, _ = ps.check_window(pad_window(raster, 2))
            rows = ["".join(map(str, row)) for row in raster]
            if slow1 and not slow2:
                f2 += 1
                print(f"*** F2-WITNESS (slow-verified) core={label} pop={sum(map(sum, raster))} — PADDING CONSTANT >= 2", flush=True)
            else:
                print(f"MISMATCH f2-candidate core={label}: slow pad1={slow1} pad2={slow2}", flush=True)
            for row in rows:
                print(row, flush=True)
        tot += cnt
        print(f"  core {ci} {label}: {cnt} pad1-SAT rings{' (CAPPED)' if cnt >= a.cap else ''}, "
              f"{time.perf_counter() - tc:.0f}s, f2 so far {f2}", flush=True)
    print(f"DONE realized {k} [{a.start},{end}): rings {tot}, f2={f2}, {time.perf_counter() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
