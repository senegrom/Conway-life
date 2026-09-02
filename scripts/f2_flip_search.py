#!/usr/bin/env python3
"""Importable single-flip boundary attack (see f2_witness_flips.py).

flip_search(rasters, k): for each (label, raster) that is a genuine f = 1
witness (bare SAT, pad^1 UNSAT), test every single-cell flip: pad^1 SAT?
then pad^2 UNSAT? Any candidate is re-verified with the slow checker.
Returns counts and finds. Used by the Modal fan-out for 15x15 witnesses.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preimage_sat as ps
from padding_flip import pad_window
from ring_orphan_search import WindowTemplate


def flip_search(rasters, k: int, log=print) -> dict:
    ring1 = WindowTemplate(k + 2, k + 2, 1)
    ring2 = WindowTemplate(k + 4, k + 4, 2)
    bare = WindowTemplate(k, k, 0)
    cells = [(i, j) for i in range(k) for j in range(k)]
    r1v = [ring1.w_var[(i + 1, j + 1)] for i, j in cells]
    r2v = [ring2.w_var[(i + 2, j + 2)] for i, j in cells]
    bv = [bare.w_var[(i, j)] for i, j in cells]
    pos = {c: p for p, c in enumerate(cells)}
    t0 = time.perf_counter()
    variants = p1sat = f1 = f2 = bad = 0
    finds, mismatches = [], []
    seen: set[tuple] = set()
    for label, raster in rasters:
        bits = [raster[i][j] for i, j in cells]
        b1 = [v if b else -v for v, b in zip(r1v, bits)]
        b2 = [v if b else -v for v, b in zip(r2v, bits)]
        bb = [v if b else -v for v, b in zip(bv, bits)]
        if ring1.has_preimage(b1) or not bare.has_preimage(bb):
            bad += 1
            continue
        for (i, j) in cells:
            variant = [row[:] for row in raster]
            variant[i][j] ^= 1
            key = tuple(map(tuple, variant))
            if key in seen:
                continue
            seen.add(key)
            variants += 1
            p = pos[(i, j)]
            a1 = b1[:]
            a1[p] = -a1[p]
            if not ring1.has_preimage(a1):
                ab = bb[:]
                ab[p] = -ab[p]
                if bare.has_preimage(ab):
                    f1 += 1
                continue
            p1sat += 1
            a2 = b2[:]
            a2[p] = -a2[p]
            if ring2.has_preimage(a2):
                continue
            slow1, _ = ps.check_window(pad_window(variant, 1))
            slow2, _ = ps.check_window(pad_window(variant, 2))
            rows = ["".join(map(str, row)) for row in variant]
            if slow1 and not slow2:
                f2 += 1
                finds.append({"from": label, "flip": [i, j], "pop": sum(map(sum, variant)), "raster": rows})
                log(f"*** F2-WITNESS (slow-verified) size={k} from={label} flip={i},{j} "
                    f"pop={sum(map(sum, variant))} — PADDING CONSTANT >= 2")
                for r in rows:
                    log(r)
            else:
                mismatches.append({"from": label, "flip": [i, j], "slow1": slow1, "slow2": slow2, "raster": rows})
                log(f"MISMATCH from={label} flip={i},{j}: slow pad1={slow1} pad2={slow2}")
    return {"witnesses": len(rasters) - bad, "bad": bad, "variants": variants, "pad1_sat": p1sat,
            "f1": f1, "f2": f2, "finds": finds, "mismatches": mismatches,
            "seconds": round(time.perf_counter() - t0, 1)}
