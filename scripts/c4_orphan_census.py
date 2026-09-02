#!/usr/bin/env python3
"""Small-population C4-symmetric orphan census (record hunt).

Smallest known Garden of Eden: 45 cells (an 11x11 orphan). A pattern P is a
Garden of Eden iff some padding of it is an orphan, so any P with pad^1(P)
an orphan and population <= 44 is a new record. C4-symmetric 11x11 cores have
31 orbits (30 of size 4 plus the centre); population <= 45 means at most 11
size-4 orbits, i.e. sum_{j<=11} C(30, j) x 2 ~ 215M candidates instead of 2^31.

search_range(j, centre, rank_start, rank_end): candidates are the j-subsets of
the 30 size-4 orbits in lexicographic order (combinatorial unranking, so any
rank range can be processed independently), with the centre cell fixed.
Per candidate one incremental pad^1 check (13x13 window, dead ring); finds
are classified bare-orphan / f=1 witness and slow-verified.
"""

from __future__ import annotations

import argparse
import sys
import time
from math import comb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preimage_sat as ps
from padding_flip import pad_window
from ring_orphan_search import WindowTemplate, cell_orbits


def c4_orbits(k: int):
    orbits = cell_orbits(k, "c4")
    centre = [o for o in orbits if len(o) == 1]
    big = [o for o in orbits if len(o) == 4]
    assert len(big) == (k * k - 1) // 4 and len(centre) == 1
    return big, centre[0]


def unrank(rank: int, n: int, j: int) -> list[int]:
    """Lexicographic j-subset of range(n) with the given rank."""
    combo = []
    x = 0
    for i in range(j):
        while True:
            c = comb(n - x - 1, j - i - 1)
            if rank < c:
                combo.append(x)
                x += 1
                break
            rank -= c
            x += 1
    return combo


def next_combo(combo: list[int], n: int) -> bool:
    """Advance to the lexicographic successor in place; False at the end."""
    j = len(combo)
    for i in range(j - 1, -1, -1):
        if combo[i] < n - j + i:
            combo[i] += 1
            for t in range(i + 1, j):
                combo[t] = combo[t - 1] + 1
            return True
    return False


def search_range(j: int, centre: int, rank_start: int, rank_end: int, k: int = 11,
                 log=print, record: int = 45) -> dict:
    big, ctr = c4_orbits(k)
    n = len(big)
    padded = WindowTemplate(k + 2, k + 2, 1)
    bare = WindowTemplate(k, k, 0)
    pad_vars = [[padded.w_var[(i + 1, jj + 1)] for i, jj in o] for o in big]
    bare_vars = [[bare.w_var[(i, jj)] for i, jj in o] for o in big]
    pad_ctr = [padded.w_var[(i + 1, jj + 1)] for i, jj in ctr]
    bare_ctr = [bare.w_var[(i, jj)] for i, jj in ctr]
    all_pad = [v for vs in pad_vars for v in vs] + pad_ctr
    all_bare = [v for vs in bare_vars for v in vs] + bare_ctr
    t0 = time.perf_counter()
    checked = 0
    finds = []
    if j > n or rank_start >= comb(n, j) or rank_start >= rank_end:
        return {"j": j, "centre": centre, "checked": 0, "finds": [], "seconds": 0.0}
    combo = unrank(rank_start, n, j) if j else []
    rank = rank_start
    while rank < rank_end:
        pos_pad = set(pad_ctr) if centre else set()
        pos_bare = set(bare_ctr) if centre else set()
        for idx in combo:
            pos_pad.update(pad_vars[idx])
            pos_bare.update(bare_vars[idx])
        checked += 1
        if not padded.has_preimage([v if v in pos_pad else -v for v in all_pad]):
            pop = 4 * j + centre
            bare_sat = bare.has_preimage([v if v in pos_bare else -v for v in all_bare])
            raster = [[0] * k for _ in range(k)]
            for idx in combo:
                for i, jj in big[idx]:
                    raster[i][jj] = 1
            if centre:
                for i, jj in ctr:
                    raster[i][jj] = 1
            slow_pad, _ = ps.check_window(pad_window(raster, 1))
            slow_bare, _ = ps.check_window(raster)
            ok = (not slow_pad) and (slow_bare == bare_sat)
            kind = "F1-WITNESS" if bare_sat else "DEAD-RINGED-ORPHAN"
            rows = ["".join(map(str, r)) for r in raster]
            finds.append({"j": j, "centre": centre, "combo": list(combo), "pop": pop, "kind": kind,
                          "verified": ok, "raster": rows})
            tag = "*** RECORD" if pop < record else "*** RECORD-TIE" if pop == record else "orphan"
            log(f"{tag} pop={pop} {kind} verified={ok} j={j} centre={centre} combo={list(combo)}")
            for r in rows:
                log(r)
        rank += 1
        if rank < rank_end and j and not next_combo(combo, n):
            break
    return {"j": j, "centre": centre, "rank_start": rank_start, "rank_end": rank_end,
            "checked": checked, "finds": finds, "seconds": round(time.perf_counter() - t0, 1)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--j", type=int, required=True)
    ap.add_argument("--centre", type=int, default=0)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int)
    a = ap.parse_args()
    n = 30
    end = a.end if a.end is not None else comb(n, a.j)
    r = search_range(a.j, a.centre, a.start, end, log=lambda s: print(s, flush=True))
    print(f"DONE c4census j={a.j} centre={a.centre} [{a.start},{end}): checked {r['checked']}, "
          f"finds {len(r['finds'])}, {r['seconds']}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
