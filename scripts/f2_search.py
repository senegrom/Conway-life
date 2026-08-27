#!/usr/bin/env python3
"""Search for f(P) = 2 witnesses: patterns whose thickness-1 padding has a
preimage patch but whose thickness-2 padding is an orphan.

A single find IMPROVES the lower bound of the Salo-Törmä optimal padding
constant (Q28820954 / LIFE-F001) from 1 to 2 — the f = 1 witnesses in
data/discoveries only justify the known bound. Enumerates symmetric K x K
cores like scripts/ring_orphan_search.py; per candidate: pad^1 preimage
check first (SAT keeps the candidate alive), then pad^2 orphan check
(UNSAT = witness). Hits are re-verified with scripts/preimage_sat.py
before being reported.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preimage_sat as ps
from padding_flip import pad_window
from ring_orphan_search import WindowTemplate, cell_orbits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=int, required=True)
    parser.add_argument("--group", choices=["d4", "c4"], required=True)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int)
    parser.add_argument("--report-every", type=float, default=120.0)
    args = parser.parse_args()

    k = args.core
    orbits = cell_orbits(k, args.group)
    n = len(orbits)
    end = args.end if args.end is not None else (1 << n)
    print(f"f2 search: core {k}x{k} {args.group}, {n} orbits, range [{args.start}, {end})", flush=True)

    ring1 = WindowTemplate(k + 2, k + 2, 1)
    ring2 = WindowTemplate(k + 4, k + 4, 2)
    r1_orbit_vars = [[ring1.w_var[(i + 1, j + 1)] for i, j in o] for o in orbits]
    r2_orbit_vars = [[ring2.w_var[(i + 2, j + 2)] for i, j in o] for o in orbits]
    all_r1 = [v for vs in r1_orbit_vars for v in vs]
    all_r2 = [v for vs in r2_orbit_vars for v in vs]

    t0 = time.perf_counter()
    last = t0
    finds = 0
    for bits in range(args.start, end):
        pos1, pos2 = set(), set()
        for idx in range(n):
            if bits >> idx & 1:
                pos1.update(r1_orbit_vars[idx])
                pos2.update(r2_orbit_vars[idx])
        if not ring1.has_preimage([v if v in pos1 else -v for v in all_r1]):
            continue  # pad^1 already an orphan: census territory, not f=2
        if ring2.has_preimage([v if v in pos2 else -v for v in all_r2]):
            now = time.perf_counter()
            if now - last > args.report_every:
                done = bits - args.start + 1
                print(f"  {done}/{end - args.start}, {done / (now - t0):.0f}/s", flush=True)
                last = now
            continue
        # Candidate: pad^1 SAT, pad^2 UNSAT. Re-verify slowly.
        raster = [[0] * k for _ in range(k)]
        for idx in range(n):
            if bits >> idx & 1:
                for i, j in orbits[idx]:
                    raster[i][j] = 1
        slow1, _ = ps.check_window(pad_window(raster, 1))
        slow2, _ = ps.check_window(pad_window(raster, 2))
        if slow1 and not slow2:
            finds += 1
            pop = sum(map(sum, raster))
            print(f"*** F2-WITNESS (verified): bits={bits} pop={pop} — LOWER BOUND -> 2", flush=True)
            for row in raster:
                print("".join(map(str, row)), flush=True)
        else:
            print(f"TEMPLATE/SLOW MISMATCH at bits={bits} — investigate!", flush=True)
    print(f"DONE f2 {k} {args.group} [{args.start},{end}): {finds} finds, {time.perf_counter() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
