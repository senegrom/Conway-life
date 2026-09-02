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


def ring_orbits(k: int, rings: int = 1):
    """D4 orbits of the cells of the `rings` outer rings of a (k+2*rings)-square
    around a kxk core."""
    n = k + 2 * rings
    return [o for o in cell_orbits(n, "d4")
            if any(min(i, j, n - 1 - i, n - 1 - j) < rings for i, j in o)]


def search(cores, start: int, end: int, k: int = 13, report_every: float = 300.0,
           log=print, quiet: bool = False, rings: int = 1, max_rings: int | None = None,
           classify: bool = False) -> dict:
    """Ring-extension search over cores[start:end]. Returns stats and finds.
    cores: list of (label, raster) with kxk rasters; `rings` outer D4 rings added."""
    n = k + 2 * rings
    rorb = ring_orbits(k, rings)
    ring1 = WindowTemplate(n + 2, n + 2, 1)
    ring2 = WindowTemplate(n + 4, n + 4, 2)
    cells = [(i, j) for i in range(n) for j in range(n)]
    r1v = {c: ring1.w_var[(c[0] + 1, c[1] + 1)] for c in cells}
    r2v = {c: ring2.w_var[(c[0] + 2, c[1] + 2)] for c in cells}
    bare = WindowTemplate(n, n, 0) if classify else None
    bv = {c: bare.w_var[c] for c in cells} if classify else None
    t0 = time.perf_counter(); last = t0
    checked = p1sat = f2 = f0 = f1 = 0
    finds, mismatches, witnesses = [], [], []
    for ci in range(start, end):
        label, core = cores[ci]
        base = [[0] * n for _ in range(n)]
        for i in range(k):
            for j in range(k):
                base[i + rings][j + rings] = core[i][j]
        for rbits in range(min(1 << len(rorb), max_rings or (1 << len(rorb)))):
            raster = [row[:] for row in base]
            for idx, o in enumerate(rorb):
                if rbits >> idx & 1:
                    for i, j in o:
                        raster[i][j] = 1
            checked += 1
            a1 = [r1v[c] if raster[c[0]][c[1]] else -r1v[c] for c in cells]
            if not ring1.has_preimage(a1):
                if classify:
                    ab = [bv[c] if raster[c[0]][c[1]] else -bv[c] for c in cells]
                    if bare.has_preimage(ab):
                        f1 += 1
                        witnesses.append((label, rbits))
                    else:
                        f0 += 1
                continue
            p1sat += 1
            a2 = [r2v[c] if raster[c[0]][c[1]] else -r2v[c] for c in cells]
            if ring2.has_preimage(a2):
                continue
            slow1, _ = ps.check_window(pad_window(raster, 1))
            slow2, _ = ps.check_window(pad_window(raster, 2))
            rows = ["".join(map(str, row)) for row in raster]
            if slow1 and not slow2:
                f2 += 1
                finds.append({"core": label, "ring": rbits, "pop": sum(map(sum, raster)), "raster": rows})
                log(f"*** F2-WITNESS (slow-verified) core={label} ring={rbits} "
                    f"pop={sum(map(sum, raster))} — PADDING CONSTANT >= 2")
                for r in rows:
                    log(r)
            else:
                mismatches.append({"core": label, "ring": rbits, "slow1": slow1, "slow2": slow2, "raster": rows})
                log(f"MISMATCH f2-candidate core={label} ring={rbits}: slow pad1={slow1} pad2={slow2}")
        now = time.perf_counter()
        if not quiet and now - last > report_every:
            log(f"  core {ci - start + 1}/{end - start}, {checked} candidates, "
                f"{checked / (now - t0):.0f}/s, pad1-SAT {p1sat}, f2 {f2}")
            last = now
    return {"start": start, "end": end, "candidates": checked, "pad1_sat": p1sat,
            "f2": f2, "f1": f1, "f0": f0, "finds": finds, "mismatches": mismatches,
            "witnesses": witnesses, "seconds": round(time.perf_counter() - t0, 1)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--core", type=int, default=13)
    ap.add_argument("--start", type=int, default=0, help="core index")
    ap.add_argument("--end", type=int)
    ap.add_argument("--only", choices=["f0", "f1", "all"], default="all")
    ap.add_argument("--report-every", type=float, default=300.0)
    ap.add_argument("--rings", type=int, default=1)
    a = ap.parse_args()
    k = a.core
    cores = harvest_cores(k)
    if a.only != "all":
        cores = [c for c in cores if c[0].startswith(a.only)]
    end = a.end if a.end is not None else len(cores)
    print(f"ring-extension f2 search: {len(cores)} cores {k}x{k} ({a.only}), "
          f"{len(ring_orbits(k))} ring orbits -> {1 << len(ring_orbits(k))} rings each; "
          f"cores [{a.start},{end})", flush=True)
    log = lambda s: print(s, flush=True)
    r = search(cores, a.start, end, k=k, report_every=a.report_every, log=log, rings=a.rings)
    print(f"DONE ringext {k} [{a.start},{end}): candidates {r['candidates']}, "
          f"pad1-SAT {r['pad1_sat']}, f2={r['f2']}, {r['seconds']:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
