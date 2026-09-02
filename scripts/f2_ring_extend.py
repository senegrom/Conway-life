#!/usr/bin/env python3
"""f = 2 hunt by ring extension of rigid cores at the size threshold.

Level-2 deadly boundaries need a side of length >= 14 (research log,
2026-09-02), and rigidity of preimage boundaries comes from orphan-adjacent
structure. So: take every D4 13x13 dead-ringed orphan and f = 1 witness
found by the deep census (rigid cores whose bare/ringed windows pin their
preimage layers) and extend each by one ring of cells (256 D4-symmetric
rings) to a 15x15 pattern P'. The core's forced preimage fence now sits one
layer further out; if the ring lets pad^1(P') be satisfiable while
pad^2(P') stays an orphan, f(P') = 2.

Per candidate: pad^1 check first (most extensions stay ringed orphans:
fast exit, counted as new 15x15 ringed orphans), pad^2 only for survivors;
any candidate is re-verified with the slow checker.
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
from ring_orphan_search import WindowTemplate, cell_orbits

BUILD = Path(r"D:\Programs\life-research\build")


def harvest_cores(k: int) -> list[tuple[str, list[list[int]]]]:
    orbits = cell_orbits(k, "d4")
    cores = {}
    for f in sorted(BUILD.glob(f"f2deep{k}-*.out")):
        t = f.read_text(encoding="utf-8")
        for m in re.finditer(r"^RINGED-ORPHAN bits=(\d+) pop=(\d+)", t, re.M):
            bits = int(m.group(1))
            raster = [[0] * k for _ in range(k)]
            for idx, o in enumerate(orbits):
                if bits >> idx & 1:
                    for i, j in o:
                        raster[i][j] = 1
            cores[bits] = ("f0", raster)
        for m in re.finditer(r"F1-WITNESS \(slow-verified\) bits=(\d+) pop=\d+ core=%d group=d4\n((?:[01]{%d}\n){%d})" % (k, k, k), t):
            bits = int(m.group(1))
            cores[bits] = ("f1", [[int(c) for c in row] for row in m.group(2).split()])
    return [(f"{kind}:{bits}", r) for bits, (kind, r) in sorted(cores.items())]


def ring_orbits(k: int):
    """D4 orbits of the ring cells of a (k+2)x(k+2) square around a kxk core."""
    n = k + 2
    return [o for o in cell_orbits(n, "d4") if any(i in (0, n - 1) or j in (0, n - 1) for i, j in o)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--core", type=int, default=13)
    ap.add_argument("--start", type=int, default=0, help="core index")
    ap.add_argument("--end", type=int)
    ap.add_argument("--only", choices=["f0", "f1", "all"], default="all")
    ap.add_argument("--report-every", type=float, default=300.0)
    a = ap.parse_args()
    k = a.core
    cores = harvest_cores(k)
    if a.only != "all":
        cores = [c for c in cores if c[0].startswith(a.only)]
    end = a.end if a.end is not None else len(cores)
    n = k + 2
    rorb = ring_orbits(k)
    print(f"ring-extension f2 search: {len(cores)} cores {k}x{k} ({a.only}), "
          f"{len(rorb)} ring orbits -> {1 << len(rorb)} rings each; cores [{a.start},{end})", flush=True)
    ring1 = WindowTemplate(n + 2, n + 2, 1)
    ring2 = WindowTemplate(n + 4, n + 4, 2)
    cells = [(i, j) for i in range(n) for j in range(n)]
    r1v = {c: ring1.w_var[(c[0] + 1, c[1] + 1)] for c in cells}
    r2v = {c: ring2.w_var[(c[0] + 2, c[1] + 2)] for c in cells}
    t0 = time.perf_counter(); last = t0
    checked = p1sat = f2 = 0
    for ci in range(a.start, end):
        label, core = cores[ci]
        base = [[0] * n for _ in range(n)]
        for i in range(k):
            for j in range(k):
                base[i + 1][j + 1] = core[i][j]
        for rbits in range(1 << len(rorb)):
            raster = [row[:] for row in base]
            for idx, o in enumerate(rorb):
                if rbits >> idx & 1:
                    for i, j in o:
                        raster[i][j] = 1
            checked += 1
            a1 = [r1v[c] if raster[c[0]][c[1]] else -r1v[c] for c in cells]
            if not ring1.has_preimage(a1):
                continue
            p1sat += 1
            a2 = [r2v[c] if raster[c[0]][c[1]] else -r2v[c] for c in cells]
            if ring2.has_preimage(a2):
                continue
            slow1, _ = ps.check_window(pad_window(raster, 1))
            slow2, _ = ps.check_window(pad_window(raster, 2))
            if slow1 and not slow2:
                f2 += 1
                print(f"*** F2-WITNESS (slow-verified) core={label} ring={rbits} "
                      f"pop={sum(map(sum, raster))} — PADDING CONSTANT >= 2", flush=True)
            else:
                print(f"MISMATCH f2-candidate core={label} ring={rbits}: slow pad1={slow1} pad2={slow2}", flush=True)
            for row in raster:
                print("".join(map(str, row)), flush=True)
        now = time.perf_counter()
        if now - last > a.report_every:
            print(f"  core {ci - a.start + 1}/{end - a.start}, {checked} candidates, "
                  f"{checked / (now - t0):.0f}/s, pad1-SAT {p1sat}, f2 {f2}", flush=True)
            last = now
    print(f"DONE ringext {k} [{a.start},{end}): candidates {checked}, pad1-SAT {p1sat}, "
          f"f2={f2}, {time.perf_counter() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
