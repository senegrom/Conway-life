#!/usr/bin/env python3
"""Deadly-word feasibility for TWO-ring extensions of 11x11 f = 1 witnesses.

P' = W (11x11 witness) + ring1 (13x13 ring) + ring2 (15x15 ring), both
rings free (image variables). For f(P') = 2 some pad^1 preimage of P' must
carry a level-2 deadly word on a side; the relevant layers are P''s own
boundary layer and the ring-1 layer above it, i.e. the witness's THIRD and
FOURTH preimage layers, which the witness does not pin directly - the
chosen rings do. For each core (all 4 rotations, so any side can be "top")
and each deadly 15-word: is there a pad^1 preimage patch (image = W on the
core, anything on the rings, dead on the window ring) whose top (d0,d1)
equals the word? Counts feasible (core, rotation, word) triples; with
--enumerate N, projects feasible preimages onto the ring pair (up to N per
triple) and tests pad^2 of each realized P'.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preimage_sat as ps
from padding_flip import pad_window
from ring_orphan_search import WindowTemplate
from goe4_qbf import _ON_COVER, _OFF_COVER
from f2_witness_flips import harvest_witnesses

OFFS = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
BUILD = Path(r"D:\Programs\life-research\build")
CENSUS = Path(__file__).resolve().parent.parent / "data" / "discoveries" / "d4-ring-orphans-11x11.txt"


def harvest_11():
    """All known 11x11 f = 1 witnesses: 4 D4 census, 60 single-flip, 1,076 double-flip."""
    out = []
    text = CENSUS.read_text(encoding="utf-8")
    for m in re.finditer(r"# F1-WITNESS 11x11 d4 population \d+ \(orbit-code (\d+)\)\n((?:[01]{11}\n){11})", text):
        out.append((f"d4:{m.group(1)}", [[int(c) for c in r] for r in m.group(2).split()]))
    census = {}
    for m in re.finditer(r"# (?:F1-WITNESS|DEAD-RINGED-ORPHAN) 11x11 d4 population \d+ \(orbit-code (\d+)\)\n((?:[01]{11}\n){11})", text):
        census[m.group(1)] = [[int(c) for c in r] for r in m.group(2).split()]
    seen = {tuple(map(tuple, r)) for _, r in out}
    for f in sorted(BUILD.glob("f2flips-d1.out")):
        t = f.read_text(encoding="utf-8")
        for m in re.finditer(r"F1-WITNESS \(slow-verified\) member=(\d+) flips=(\S+) pop=\d+\n((?:[01]{11}\n){11})", t):
            r = [[int(c) for c in row] for row in m.group(3).split()]
            key = tuple(map(tuple, r))
            if key not in seen:
                seen.add(key)
                out.append((f"d1:{m.group(1)}:{m.group(2)}", r))
        for m in re.finditer(r"^F1 member=(\d+) flips=(\S+) pop=\d+$", t, re.M):
            base = census.get(m.group(1))
            if base is None:
                continue
            r = [row[:] for row in base]
            for fl in m.group(2).split(";"):
                i, j = map(int, fl.split(","))
                r[i][j] ^= 1
            key = tuple(map(tuple, r))
            if key not in seen:
                seen.add(key)
                out.append((f"d1:{m.group(1)}:{m.group(2)}", r))
    for label, r in harvest_witnesses(11):
        key = tuple(map(tuple, r))
        if key not in seen:
            seen.add(key)
            out.append((label, r))
    return out


def rot(r):
    return [list(x) for x in zip(*r[::-1])]


def build(core, k: int, rings: int):
    """CNF over a preimage patch of the pad^1 window of P' = core + rings.
    Core cells: image fixed; ring cells: image variables; window ring: dead."""
    n = k + 2 * rings
    W = n + 2
    X = W + 2
    nv = 0
    xv = {}
    for y in range(X):
        for x in range(X):
            nv += 1
            xv[(y, x)] = nv
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
                continue
            py, px = y - 1, x - 1
            d = min(py, px, n - 1 - py, n - 1 - px)
            if d < rings:
                nv += 1
                t = nv
                ring_img[(py, px)] = t
                for value, mask in _ON_COVER:
                    term(nb, value, mask, [t])
                for value, mask in _OFF_COVER:
                    term(nb, value, mask, [-t])
            else:
                if core[py - rings][px - rings]:
                    for value, mask in _OFF_COVER:
                        term(nb, value, mask, [])
                else:
                    for value, mask in _ON_COVER:
                        term(nb, value, mask, [])
    return clauses, nv, ring_img, xv, n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rings", type=int, default=2)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int)
    ap.add_argument("--words", type=Path, default=BUILD / "deadly15.txt")
    ap.add_argument("--enumerate", type=int, default=0,
                    help="cap of realized ring pairs per feasible (core, rot, word)")
    a = ap.parse_args()
    from pysat.solvers import Solver
    k = 11
    cores = harvest_11()
    end = a.end if a.end is not None else len(cores)
    words = [tuple(l.split()) for l in a.words.read_text().split("\n") if l.strip()]
    n = k + 2 * a.rings
    assert n == 15, "deadly15 words assume a 15-wide top side"
    ring2 = WindowTemplate(n + 4, n + 4, 2)
    cells = [(i, j) for i in range(n) for j in range(n)]
    r2v = {c: ring2.w_var[(c[0] + 2, c[1] + 2)] for c in cells}
    print(f"two-ring anchored: {len(cores)} 11x11 witness cores, cores [{a.start},{end}), "
          f"{len(words)} words x 4 rotations", flush=True)
    t0 = time.perf_counter()
    feasible = f2 = tested = 0
    for ci in range(a.start, end):
        label, core = cores[ci]
        fc = 0
        for rotation in range(4):
            clauses, nv, ring_img, xv, _ = build(core, k, a.rings)
            rvars = list(ring_img.items())
            with Solver(name="g3", bootstrap_with=clauses) as s:
                for d0, d1 in words:
                    assum = []
                    for i in range(n):
                        v0 = xv[(2, 2 + i)]
                        v1 = xv[(1, 2 + i)]
                        assum.append(v0 if d0[i] == "1" else -v0)
                        assum.append(v1 if d1[i] == "1" else -v1)
                    if not s.solve(assumptions=assum):
                        continue
                    feasible += 1
                    fc += 1
                    print(f"  FEASIBLE core={label} rot={rotation} word={d0}/{d1}", flush=True)
                    if not a.enumerate:
                        continue
                    seen = set()
                    cnt = 0
                    while cnt < a.enumerate and s.solve(assumptions=assum):
                        m = set(l for l in s.get_model() if l > 0)
                        rb = tuple(1 if v in m else 0 for _, v in rvars)
                        cnt += 1
                        s.add_clause([-v if v in m else v for _, v in rvars])
                        if rb in seen:
                            continue
                        seen.add(rb)
                        raster = [[0] * n for _ in range(n)]
                        for i in range(k):
                            for j in range(k):
                                raster[i + a.rings][j + a.rings] = core[i][j]
                        for ((i, j), _), b in zip(rvars, rb):
                            raster[i][j] = b
                        tested += 1
                        a2 = [r2v[c] if raster[c[0]][c[1]] else -r2v[c] for c in cells]
                        if ring2.has_preimage(a2):
                            continue
                        slow1, _ = ps.check_window(pad_window(raster, 1))
                        slow2, _ = ps.check_window(pad_window(raster, 2))
                        rows = ["".join(map(str, row)) for row in raster]
                        if slow1 and not slow2:
                            f2 += 1
                            print(f"*** F2-WITNESS (slow-verified) core={label} rot={rotation} "
                                  f"word={d0}/{d1} pop={sum(map(sum, raster))} — PADDING CONSTANT >= 2",
                                  flush=True)
                        else:
                            print(f"MISMATCH core={label}: slow pad1={slow1} pad2={slow2}", flush=True)
                        for row in rows:
                            print(row, flush=True)
            core = rot(core)
        print(f"  core {ci} {label}: {fc} feasible (rot,word) pairs; total feasible {feasible}, "
              f"pad2-tested {tested}, f2 {f2}, {time.perf_counter() - t0:.0f}s", flush=True)
    print(f"DONE two-ring anchored [{a.start},{end}): feasible {feasible}, pad2-tested {tested}, "
          f"f2={f2}, {time.perf_counter() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
