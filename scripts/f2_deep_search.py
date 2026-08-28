#!/usr/bin/env python3
"""Deep-ring search: enumerate symmetric K x K cores and find every P whose
thickness-2 padding pad^2(P) is an orphan, classified by flip point:

    pad^1(P) SAT            -> F2-WITNESS: f(P) = 2, IMPROVES the known
                               lower bound of the Salo-Torma padding
                               constant (Q28820954 / LIFE-F001) from 1 to 2
    pad^1 UNSAT, bare SAT   -> F1-WITNESS: f(P) = 1 (new witness)
    pad^1 UNSAT, bare UNSAT -> RINGED-ORPHAN: f(P) = 0 (census find)

Ordering exploits rarity: one incremental pad^2 check per candidate (SAT =
common exit); only pad^2-orphans (rare) pay the pad^1 and bare checks. Since
pad^1-orphan implies pad^2-orphan, the pad^1 census at this size falls out
as a byproduct. F1/F2 finds are re-verified with the slow exhaustively
validated checker (scripts/preimage_sat.py) before being reported; F0 finds
are compact one-liners (raster reconstructible from the orbit code), with
the first few per run slow-verified as a spot check.
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


def raster_of(bits: int, orbits, k: int) -> list[list[int]]:
    raster = [[0] * k for _ in range(k)]
    for idx, orbit in enumerate(orbits):
        if bits >> idx & 1:
            for i, j in orbit:
                raster[i][j] = 1
    return raster


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=int, required=True)
    parser.add_argument("--group", choices=["d4", "c4"], required=True)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int)
    parser.add_argument("--report-every", type=float, default=300.0)
    parser.add_argument("--spot-verify-f0", type=int, default=3,
                        help="slow-verify the first N f=0 finds")
    args = parser.parse_args()

    k = args.core
    orbits = cell_orbits(k, args.group)
    n = len(orbits)
    end = args.end if args.end is not None else (1 << n)
    print(f"deep f2 search: core {k}x{k} {args.group}, {n} orbits, "
          f"range [{args.start}, {end})", flush=True)

    ring2 = WindowTemplate(k + 4, k + 4, 2)
    ring1 = WindowTemplate(k + 2, k + 2, 1)
    bare = WindowTemplate(k, k, 0)
    r2_vars = [[ring2.w_var[(i + 2, j + 2)] for i, j in o] for o in orbits]
    r1_vars = [[ring1.w_var[(i + 1, j + 1)] for i, j in o] for o in orbits]
    b_vars = [[bare.w_var[(i, j)] for i, j in o] for o in orbits]
    all_r2 = [v for vs in r2_vars for v in vs]
    all_r1 = [v for vs in r1_vars for v in vs]
    all_b = [v for vs in b_vars for v in vs]

    t0 = time.perf_counter()
    last = t0
    counts = {0: 0, 1: 0, 2: 0}
    spot_left = args.spot_verify_f0
    for bits in range(args.start, end):
        pos2 = set()
        for idx in range(n):
            if bits >> idx & 1:
                pos2.update(r2_vars[idx])
        if ring2.has_preimage([v if v in pos2 else -v for v in all_r2]):
            now = time.perf_counter()
            if now - last > args.report_every:
                done = bits - args.start + 1
                print(f"  {done}/{end - args.start}, {done / (now - t0):.0f}/s, "
                      f"finds f0={counts[0]} f1={counts[1]} f2={counts[2]}",
                      flush=True)
                last = now
            continue

        # pad^2 orphan. Classify by flip point.
        pos1 = {r1_vars[idx][m] for idx in range(n) if bits >> idx & 1
                for m in range(len(r1_vars[idx]))}
        pad1_sat = ring1.has_preimage([v if v in pos1 else -v for v in all_r1])
        raster = raster_of(bits, orbits, k)
        pop = sum(map(sum, raster))

        if pad1_sat:
            slow1, _ = ps.check_window(pad_window(raster, 1))
            slow2, _ = ps.check_window(pad_window(raster, 2))
            if slow1 and not slow2:
                counts[2] += 1
                print(f"*** F2-WITNESS (slow-verified) bits={bits} pop={pop} "
                      f"core={k} group={args.group} — PADDING CONSTANT >= 2",
                      flush=True)
            else:
                print(f"MISMATCH f2-candidate bits={bits}: slow pad1={slow1} "
                      f"pad2={slow2} — investigate!", flush=True)
            for row in raster:
                print("".join(map(str, row)), flush=True)
            continue

        posb = {b_vars[idx][m] for idx in range(n) if bits >> idx & 1
                for m in range(len(b_vars[idx]))}
        bare_sat = bare.has_preimage([v if v in posb else -v for v in all_b])
        if bare_sat:
            slow0, _ = ps.check_window(raster)
            slow1, _ = ps.check_window(pad_window(raster, 1))
            if slow0 and not slow1:
                counts[1] += 1
                print(f"*** F1-WITNESS (slow-verified) bits={bits} pop={pop} "
                      f"core={k} group={args.group}", flush=True)
            else:
                print(f"MISMATCH f1-candidate bits={bits}: slow bare={slow0} "
                      f"pad1={slow1} — investigate!", flush=True)
            for row in raster:
                print("".join(map(str, row)), flush=True)
        else:
            counts[0] += 1
            tag = ""
            if spot_left > 0:
                spot_left -= 1
                slow0, _ = ps.check_window(raster)
                slow1, _ = ps.check_window(pad_window(raster, 1))
                tag = (" [spot-verified]" if not slow0 and not slow1
                       else " [SPOT MISMATCH — investigate!]")
            print(f"RINGED-ORPHAN bits={bits} pop={pop}{tag}", flush=True)

    print(f"DONE deep {k} {args.group} [{args.start},{end}): "
          f"f0={counts[0]} f1={counts[1]} f2={counts[2]}, "
          f"{time.perf_counter() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
