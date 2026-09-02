#!/usr/bin/env python3
"""CPU reference for a GPU preimage pre-filter: stochastic local search for a
one-step preimage patch of a fully specified window (here pad^2 of a
pattern). A found patch is verified exactly by stepping; failure to find one
within the budget says nothing (those instances go to the SAT solver). The
census pipeline only needs UNSAT claims to be exact, so this is sound as a
SAT-side accelerator.

Energy = number of window cells whose image differs from the target; moves
flip one patch cell (affects <= 9 image cells); Metropolis acceptance with a
geometric temperature schedule and random restarts.
"""

from __future__ import annotations

import argparse
import math
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preimage_sat import life_out, check_window  # noqa: E402
from padding_flip import pad_window  # noqa: E402
from ring_orphan_search import cell_orbits  # noqa: E402


def anneal(window, steps: int = 20000, restarts: int = 3, noise: float = 0.2,
           rng: random.Random | None = None):
    """Focused local search (WalkSAT-style): pick a wrong image cell, flip the
    patch cell among its 9 that best reduces the energy (random with prob
    `noise`). Return a verified preimage patch or None."""
    rng = rng or random.Random()
    h, w = len(window), len(window[0])
    ph, pw = h + 2, w + 2
    for _ in range(restarts):
        patch = [[rng.randint(0, 1) for _ in range(pw)] for _ in range(ph)]

        def img(i, j):
            c = 0
            for di in (0, 1, 2):
                row = patch[i + di]
                c += row[j] + row[j + 1] + row[j + 2]
            centre = patch[i + 1][j + 1]
            c -= centre
            return 1 if c == 3 or (c == 2 and centre == 1) else 0

        wrong = [[img(i, j) != window[i][j] for j in range(w)] for i in range(h)]
        wrong_set = {(i, j) for i in range(h) for j in range(w) if wrong[i][j]}
        if not wrong_set:
            return patch

        def delta_of(r, c):
            patch[r][c] ^= 1
            d = 0
            touched = []
            for i in range(max(0, r - 2), min(h, r + 1)):
                for j in range(max(0, c - 2), min(w, c + 1)):
                    nw = img(i, j) != window[i][j]
                    if nw != wrong[i][j]:
                        d += 1 if nw else -1
                        touched.append((i, j, nw))
            patch[r][c] ^= 1
            return d, touched

        for s in range(steps):
            i, j = rng.choice(tuple(wrong_set)) if len(wrong_set) < 64 else next(iter(wrong_set))
            cand = [(i + di, j + dj) for di in (0, 1, 2) for dj in (0, 1, 2)]
            if rng.random() < noise:
                r, c = rng.choice(cand)
                d, touched = delta_of(r, c)
            else:
                best = None
                for r, c in cand:
                    d, touched = delta_of(r, c)
                    if best is None or d < best[0]:
                        best = (d, touched, r, c)
                d, touched, r, c = best
            patch[r][c] ^= 1
            for ii, jj, nw in touched:
                wrong[ii][jj] = nw
                if nw:
                    wrong_set.add((ii, jj))
                else:
                    wrong_set.discard((ii, jj))
            if not wrong_set:
                return patch
    return None


def verify(window, patch) -> bool:
    from preimage_sat import verify_patch
    return verify_patch(window, patch)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--k", type=int, default=15)
    ap.add_argument("--samples", type=int, default=50)
    ap.add_argument("--steps", type=int, default=20000)
    ap.add_argument("--restarts", type=int, default=3)
    ap.add_argument("--density", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    orbits = cell_orbits(a.k, "d4")
    found = sat = unsat = 0
    t_anneal = t_sat = 0.0
    fails_on_sat = 0
    for _ in range(a.samples):
        raster = [[0] * a.k for _ in range(a.k)]
        for o in orbits:
            if rng.random() < a.density:
                for i, j in o:
                    raster[i][j] = 1
        window = pad_window(raster, 2)
        t = time.perf_counter()
        patch = anneal(window, a.steps, a.restarts, rng=rng)
        t_anneal += time.perf_counter() - t
        if patch is not None:
            assert verify(window, patch)
            found += 1
        t = time.perf_counter()
        has, _ = check_window(window)
        t_sat += time.perf_counter() - t
        if has:
            sat += 1
            if patch is None:
                fails_on_sat += 1
        else:
            unsat += 1
    print(f"k={a.k} density={a.density}: {a.samples} random D4 patterns; SAT {sat}, UNSAT {unsat}; "
          f"anneal found {found} (missed {fails_on_sat} of the SAT ones); "
          f"anneal {t_anneal / a.samples * 1000:.0f} ms/candidate vs SAT {t_sat / a.samples * 1000:.0f} ms/candidate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
