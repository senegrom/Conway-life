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


def gen2_attack(rasters, k: int, sample_mod: int = 10, log=print, residues=(0,)) -> dict:
    """Second-generation boundary attack. For each (label, raster) f = 1
    witness: enumerate its single-flip variants, classify those that are
    themselves f = 1 witnesses (pad^1 UNSAT, bare SAT) = generation 2, keep a
    deterministic 1/sample_mod sample by raster hash, and run the single-flip
    attack on each sampled gen-2 witness. `residues` selects which hash
    residues (mod sample_mod) are attacked: (0,) = the 10% sample, (1..9) =
    the remaining 90%, all residues = 100%. Returns totals, finds, and the
    full gen-2 identifier list (parent label, i, j) for reproducibility."""
    residues = set(residues)
    import hashlib

    ring1 = WindowTemplate(k + 2, k + 2, 1)
    ring2 = WindowTemplate(k + 4, k + 4, 2)
    bare = WindowTemplate(k, k, 0)
    cells = [(i, j) for i in range(k) for j in range(k)]
    r1v = [ring1.w_var[(i + 1, j + 1)] for i, j in cells]
    r2v = [ring2.w_var[(i + 2, j + 2)] for i, j in cells]
    bv = [bare.w_var[(i, j)] for i, j in cells]
    pos = {c: p for p, c in enumerate(cells)}
    t0 = time.perf_counter()
    gen2, sampled, variants, p1sat, f2 = [], 0, 0, 0, 0
    finds, mismatches = [], []

    def attack(label, raster):
        nonlocal variants, p1sat, f2
        bits = [raster[i][j] for i, j in cells]
        b1 = [v if b else -v for v, b in zip(r1v, bits)]
        b2 = [v if b else -v for v, b in zip(r2v, bits)]
        for (i, j) in cells:
            p = pos[(i, j)]
            a1 = b1[:]
            a1[p] = -a1[p]
            variants += 1
            if not ring1.has_preimage(a1):
                continue
            p1sat += 1
            a2 = b2[:]
            a2[p] = -a2[p]
            if ring2.has_preimage(a2):
                continue
            variant = [row[:] for row in raster]
            variant[i][j] ^= 1
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

    for label, raster in rasters:
        bits = [raster[i][j] for i, j in cells]
        b1 = [v if b else -v for v, b in zip(r1v, bits)]
        bb = [v if b else -v for v, b in zip(bv, bits)]
        for (i, j) in cells:
            p = pos[(i, j)]
            a1 = b1[:]
            a1[p] = -a1[p]
            if ring1.has_preimage(a1):
                continue
            ab = bb[:]
            ab[p] = -ab[p]
            if not bare.has_preimage(ab):
                continue
            gen2.append((label, i, j))
            variant = [row[:] for row in raster]
            variant[i][j] ^= 1
            h = hashlib.blake2b("".join("".join(map(str, r)) for r in variant).encode(), digest_size=8).digest()
            if int.from_bytes(h, "big") % sample_mod not in residues:
                continue
            sampled += 1
            attack(f"{label}^{i},{j}", variant)
    return {"parents": len(rasters), "gen2": len(gen2), "gen2_ids": gen2, "sampled": sampled,
            "variants": variants, "pad1_sat": p1sat, "f2": f2, "finds": finds,
            "mismatches": mismatches, "seconds": round(time.perf_counter() - t0, 1)}
