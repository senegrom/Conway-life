#!/usr/bin/env python3
"""Exact width bounds for fixed-height orphans, by BFS over reachable-state sets.

A height-h window is an orphan iff the column-transfer NFA's reachable set
(states = pairs of consecutive (h+2)-bit preimage columns) becomes empty. The
narrowest orphan of height h is therefore the length of the shortest word that
empties the initial (full) set.

BFS over sets, level by level, with two sound reductions:
  * dedup: identical sets are merged;
  * antichain: if S subset T then any word emptying T also empties S, so
    supersets are dropped (kept sets are inclusion-minimal).
Both preserve the shortest emptying word, so reaching depth W with no empty set
PROVES no orphan of that height has width <= W.

Sets are packed bitsets (n*n bits in uint64 words), so domination tests are
vectorised. Progress is streamed per depth (Modal shows it live). --mirror
restricts columns to vertically mirror-symmetric ones: a smaller alphabet whose
language contains Eker's 45x45 orphan, so the search then decides the narrowest
MIRROR-SYMMETRIC orphan.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goe5_beam import build_valid, mirror_letters, step, word_to_window  # noqa: E402


def pack(S: np.ndarray) -> np.ndarray:
    """Boolean n x n set -> packed uint64 vector."""
    flat = S.ravel()
    pad = (-flat.size) % 64
    if pad:
        flat = np.concatenate([flat, np.zeros(pad, dtype=bool)])
    return np.packbits(flat.reshape(-1, 64), axis=1, bitorder="little").view(np.uint64).ravel()


def minimal_filter(packed: np.ndarray, order: np.ndarray, log=None, report_every: float = 30.0):
    """Indices (in `order`, ascending popcount) of inclusion-minimal sets.
    packed: (m, words) uint64. Keeps sets not containing any earlier kept set."""
    keep_idx: list[int] = []
    keep_rows: list[np.ndarray] = []
    t0 = time.time()
    last = t0
    for pos, i in enumerate(order):
        p = packed[i]
        if keep_rows:
            K = np.stack(keep_rows)
            # q subset p  <=>  (~p & q) == 0 for all words
            if np.any(~np.any(np.bitwise_and(~p, K), axis=1)):
                continue
        keep_idx.append(int(i))
        keep_rows.append(p)
        now = time.time()
        if log and now - last > report_every:
            log(f"    minimal-filter {pos + 1}/{len(order)}, kept {len(keep_idx)}, {now - t0:.0f}s")
            last = now
    return keep_idx


def bfs(h: int, max_depth: int, cap: int, mirror: bool, log=print, antichain: bool = True,
        filter_cap: int = 40000):
    valid = build_valid(h)
    n = 1 << (h + 2)
    letters = mirror_letters(h) if mirror else list(range(1 << h))
    log(f"height {h}: {len(letters)} column letters, {n * n} NFA states, "
        f"antichain={antichain}, cap={cap}")
    frontier = [(np.ones((n, n), dtype=bool), [])]
    t0 = time.time()
    for d in range(1, max_depth + 1):
        seen = {}
        order_words = []
        for S, word in frontier:
            for L in letters:
                T = step(S, valid[L])
                if not T.any():
                    return {"orphan_width": d, "word": word + [L],
                            "seconds": round(time.time() - t0)}
                key = T.tobytes()
                if key not in seen:
                    seen[key] = (T, word + [L])
        items = list(seen.values())
        sizes = np.array([int(S.sum()) for S, _ in items])
        if antichain and len(items) <= filter_cap:
            packed = np.stack([pack(S) for S, _ in items])
            order = np.argsort(sizes)
            keep = minimal_filter(packed, order, log=log)
            items = [items[i] for i in keep]
            note = f"{len(seen)} distinct -> {len(items)} minimal"
        else:
            note = f"{len(seen)} distinct (no antichain filter)"
        frontier = items
        log(f"  depth {d}: {note}, smallest {int(sizes.min())}, {round(time.time() - t0)}s")
        if len(frontier) > cap:
            return {"orphan_width": None, "stopped": "cap", "proved_no_orphan_up_to": d,
                    "frontier": len(frontier), "seconds": round(time.time() - t0)}
    return {"orphan_width": None, "stopped": "max_depth", "proved_no_orphan_up_to": max_depth,
            "frontier": len(frontier), "seconds": round(time.time() - t0)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--height", type=int, default=5)
    ap.add_argument("--max-depth", type=int, default=46)
    ap.add_argument("--cap", type=int, default=200000)
    ap.add_argument("--mirror", action="store_true")
    ap.add_argument("--no-antichain", action="store_true")
    a = ap.parse_args()
    r = bfs(a.height, a.max_depth, a.cap, a.mirror, log=lambda s: print(s, flush=True),
            antichain=not a.no_antichain)
    print(r, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
