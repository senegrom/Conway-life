#!/usr/bin/env python3
"""Rigorous lower bounds on the width of fixed-height orphans, in polynomial time.

Setting. Reading a height-h window column by column, its preimages are the runs
of an NFA whose states are pairs of consecutive (h+2)-bit preimage columns; the
window is an orphan iff the reachable set (from the full set) becomes empty.
The narrowest orphan of height h is the length of the shortest emptying word.
Exact BFS over reachable sets (goe5_exact.py) is exponential; the certificates
below are polynomial.

k = 0 certificate. C_0 = all states, C_{n+1} = C_n & AND_L step(C_n, L).
By induction R_w contains C_{|w|} for every word w, so C_n nonempty means no
height-h orphan of width n, and stabilisation at a nonempty set proves that
height has no orphan of any width.

k-lookback certificate (strictly stronger). Index the sets by the last k
columns read: a family {C^u}, u in letters^k. Induction hypothesis: R_w
contains C^{suffix_k(w)}_{|w|}. Since suffix_k(wL) = (u[1:], L) whenever
suffix_k(w) = u,

    C^v_{n+1} = AND over u with u[1:] == v[:-1] of step(C^u_n, v[-1])

keeps the hypothesis true. All indices nonempty through iteration N proves no
height-h orphan of width <= N; stabilisation proves none at any width. As k
grows this converges to the exact BFS, at 2^(hk) sets per iteration.
"""

from __future__ import annotations

import argparse
import itertools
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goe5_beam import build_valid, mirror_letters, step, step_all  # noqa: E402


def fixed_point(h: int, max_iter: int = 200, mirror: bool = False, log=print, valid=None):
    """k = 0 certificate."""
    if valid is None:
        valid = build_valid(h)
    n = 1 << (h + 2)
    letters = mirror_letters(h) if mirror else list(range(1 << h))
    C = np.ones((n, n), dtype=bool)
    sizes = [int(C.sum())]
    t0 = time.time()
    for it in range(1, max_iter + 1):
        nxt = C.copy()
        for L in letters:
            nxt &= step(C, valid[L])
            if not nxt.any():
                break
        size = int(nxt.sum())
        sizes.append(size)
        log(f"  h={h} k=0{' mirror' if mirror else ''} iter {it}: |C| = {size}")
        if size == 0:
            return {"height": h, "k": 0, "mirror": mirror, "proved_no_orphan_up_to": it - 1,
                    "sizes": sizes, "seconds": round(time.time() - t0, 1)}
        if np.array_equal(nxt, C):
            return {"height": h, "k": 0, "mirror": mirror, "stabilised_at": it,
                    "no_orphan_any_width": True, "certificate_size": size, "sizes": sizes,
                    "seconds": round(time.time() - t0, 1)}
        C = nxt
    return {"height": h, "k": 0, "mirror": mirror, "max_iter": max_iter, "sizes": sizes,
            "seconds": round(time.time() - t0, 1)}


def fixed_point_indexed(h: int, k: int = 1, max_iter: int = 200, mirror: bool = False,
                        log=print, valid=None, report_every: int = 1):
    """k-lookback certificate (k >= 1)."""
    if valid is None:
        valid = build_valid(h)
    n = 1 << (h + 2)
    letters = mirror_letters(h) if mirror else list(range(1 << h))
    lidx = {L: i for i, L in enumerate(letters)}
    idx = list(itertools.product(letters, repeat=k))
    C = {u: np.ones((n, n), dtype=bool) for u in idx}
    # For each index u, the successors that can follow it.
    t0 = time.time()
    hist = []
    for it in range(1, max_iter + 1):
        steps = {}                      # (u, L) -> step(C^u, L), computed letter-batched
        for u in idx:
            T = step_all(C[u], valid)   # (all letters, n, n) in NFA letter order
            steps[u] = T
        nxt = {}
        for v in idx:
            L = v[-1]
            acc = None
            for u in idx:
                if u[1:] != v[:-1]:
                    continue
                T = steps[u][L]
                acc = T.copy() if acc is None else (acc & T)
            nxt[v] = acc if acc is not None else np.zeros((n, n), dtype=bool)
        sizes = [int(S.sum()) for S in nxt.values()]
        smallest = min(sizes)
        hist.append(smallest)
        if it % report_every == 0 or smallest == 0:
            log(f"  h={h} k={k}{' mirror' if mirror else ''} iter {it}: smallest index set {smallest}, "
                f"nonempty {sum(1 for s in sizes if s)}/{len(idx)}, {round(time.time() - t0)}s")
        if smallest == 0:
            return {"height": h, "k": k, "mirror": mirror, "proved_no_orphan_up_to": it - 1,
                    "history": hist, "seconds": round(time.time() - t0, 1)}
        if all(np.array_equal(nxt[v], C[v]) for v in idx):
            return {"height": h, "k": k, "mirror": mirror, "stabilised_at": it,
                    "no_orphan_any_width": True, "smallest": smallest, "history": hist,
                    "seconds": round(time.time() - t0, 1)}
        C = nxt
    return {"height": h, "k": k, "mirror": mirror, "max_iter": max_iter, "history": hist,
            "seconds": round(time.time() - t0, 1)}


def verify_certificate(C: np.ndarray, valid, letters) -> bool:
    """C nonempty and C subset step(C, L) for every letter L (k = 0 certificate)."""
    if not C.any():
        return False
    return all(int((C & ~step(C, valid[L])).sum()) == 0 for L in letters)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--heights", type=int, nargs="+", default=[4, 5])
    ap.add_argument("--k", type=int, default=1)
    ap.add_argument("--mirror", action="store_true")
    ap.add_argument("--max-iter", type=int, default=200)
    a = ap.parse_args()
    for h in a.heights:
        valid = build_valid(h)
        f = fixed_point if a.k == 0 else (lambda *args, **kw: fixed_point_indexed(*args, k=a.k, **kw))
        r = (fixed_point(h, a.max_iter, a.mirror, log=lambda s: print(s, flush=True), valid=valid)
             if a.k == 0 else
             fixed_point_indexed(h, a.k, a.max_iter, a.mirror, log=lambda s: print(s, flush=True), valid=valid))
        print(r, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
