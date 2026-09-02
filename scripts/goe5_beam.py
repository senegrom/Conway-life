#!/usr/bin/env python3
"""Narrow orphans of fixed height by beam search over the column transfer NFA.

An h x w window is an orphan iff no preimage patch exists. Reading the window
column by column, the preimage is a run of the NFA whose states are pairs of
consecutive (h+2)-bit preimage columns (c1, c2); on pattern column letter L
the state (c1, c2) may move to (c2, c3) iff Life applied to the three columns
c1, c2, c3 yields L. All states are initial (free margins); a window is an
orphan iff the set of reachable states becomes EMPTY after its last column.

Beam search: expand the current reachable-state sets by every letter, keep the
B sets with the fewest states, stop when one is empty (an orphan of that
width, verified with the exact SAT checker). Height 4 must never succeed
(Wade 2023); height 5 has a known 45-wide orphan; narrower ones are the target.

Reachable sets are boolean 128x128 matrices S[c1, c2]; valid[L, c1, c2, c3]
is precomputed (h = 5: 32 x 128 x 128 x 128 booleans).
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preimage_sat import life_out, check_window  # noqa: E402


def build_valid(h: int) -> np.ndarray:
    """valid[L, c1, c2, c3] = (image column of (c1,c2,c3) == L)."""
    m = h + 2
    n = 1 << m
    cols = np.arange(n, dtype=np.int64)
    bits = ((cols[:, None] >> np.arange(m)) & 1).astype(np.int8)  # [col, row]
    # neighbourhood counts per output row i (0..h-1): rows i..i+2 of the three columns
    img = np.zeros((n, n, n), dtype=np.int64)  # image letter for (c1,c2,c3)
    b1 = bits[:, None, None, :]
    b2 = bits[None, :, None, :]
    b3 = bits[None, None, :, :]
    for i in range(h):
        s = np.zeros((n, n, n), dtype=np.int8)
        for r in (i, i + 1, i + 2):
            s = s + b1[..., r] + b2[..., r] + b3[..., r]
        centre = b2[..., i + 1]
        cnt = s - centre
        alive = (cnt == 3) | ((cnt == 2) & (centre == 1))
        img |= alive.astype(np.int64) << i
    valid = np.zeros((1 << h, n, n, n), dtype=bool)
    for L in range(1 << h):
        valid[L] = img == L
    return valid


def step(S: np.ndarray, valid_L: np.ndarray) -> np.ndarray:
    """Successor reachable set: T[c2, c3] = OR_c1 (S[c1,c2] & valid[c1,c2,c3])."""
    return (S[:, :, None] & valid_L).any(axis=0)


def beam_search(h: int, valid: np.ndarray, beam: int, max_w: int, rng: random.Random,
                log=print, noise: float = 0.0):
    n = 1 << (h + 2)
    letters = 1 << h
    start = np.ones((n, n), dtype=bool)
    frontier = [(int(start.sum()), [], start)]
    for w in range(1, max_w + 1):
        cand = []
        seen = set()
        for _, word, S in frontier:
            for L in range(letters):
                T = step(S, valid[L])
                size = int(T.sum())
                if size == 0:
                    return word + [L]
                key = T.tobytes()
                if key in seen:
                    continue
                seen.add(key)
                score = size * (1.0 + noise * rng.random()) if noise else size
                cand.append((score, word + [L], T))
        cand.sort(key=lambda t: t[0])
        frontier = cand[:beam]
        log(f"  width {w}: best reachable-set size {frontier[0][0]:.0f} of {n * n}, "
            f"{len(cand)} distinct candidates")
    return None


def word_to_window(word, h: int):
    return [[(L >> i) & 1 for L in word] for i in range(h)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--height", type=int, default=5)
    ap.add_argument("--beam", type=int, default=200)
    ap.add_argument("--max-width", type=int, default=46)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--noise", type=float, default=0.0)
    ap.add_argument("--validate", type=int, default=0, help="cross-check NFA vs SAT on N random windows")
    a = ap.parse_args()
    t0 = time.perf_counter()
    valid = build_valid(a.height)
    print(f"height {a.height}: valid table built in {time.perf_counter() - t0:.1f}s", flush=True)
    rng = random.Random(a.seed)
    if a.validate:
        n = 1 << (a.height + 2)
        bad = 0
        for _ in range(a.validate):
            w = rng.randint(1, 6)
            word = [rng.randrange(1 << a.height) for _ in range(w)]
            S = np.ones((n, n), dtype=bool)
            for L in word:
                S = step(S, valid[L])
            nfa = bool(S.any())
            sat, _ = check_window(word_to_window(word, a.height))
            if nfa != sat:
                bad += 1
        print(f"validate: {a.validate} random windows, NFA/SAT disagreements: {bad}", flush=True)
        return 0 if bad == 0 else 1
    word = beam_search(a.height, valid, a.beam, a.max_width, rng, log=lambda s: print(s, flush=True),
                       noise=a.noise)
    if word is None:
        print(f"no orphan found up to width {a.max_width} (beam {a.beam})", flush=True)
        return 0
    window = word_to_window(word, a.height)
    sat, _ = check_window(window)
    print(f"*** ORPHAN height {a.height} width {len(word)} (SAT check: {'ORPHAN confirmed' if not sat else 'MISMATCH'})",
          flush=True)
    for row in window:
        print("".join(map(str, row)), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def good_set(valid: np.ndarray, suffix: list[int]) -> np.ndarray:
    """States (c1, c2) from which the column word `suffix` has a run.
    Backward: good_i[c1,c2] = OR_c3 (valid[L_i][c1,c2,c3] & good_{i+1}[c2,c3])."""
    n = valid.shape[1]
    good = np.ones((n, n), dtype=bool)
    for L in reversed(suffix):
        good = (valid[L] & good[None, :, :]).any(axis=2)
    return good


def beam_prefix(h: int, valid: np.ndarray, suffix: list[int], beam: int, max_prefix: int,
                rng: random.Random, log=print, noise: float = 0.0, letters_allowed=None):
    """Shortest prefix (by beam search) whose reachable set is disjoint from the
    states that can complete `suffix`; prefix + suffix is then an orphan."""
    n = 1 << (h + 2)
    letters = letters_allowed if letters_allowed is not None else list(range(1 << h))
    good = good_set(valid, suffix)
    start = np.ones((n, n), dtype=bool)
    if not (start & good).any():
        return []
    frontier = [(int((start & good).sum()), [], start)]
    for w in range(1, max_prefix + 1):
        cand = []
        seen = set()
        for _, word, S in frontier:
            for L in letters:
                T = step(S, valid[L])
                bad = int((T & good).sum())
                if bad == 0:
                    return word + [L]
                key = T.tobytes()
                if key in seen:
                    continue
                seen.add(key)
                score = bad * (1.0 + noise * rng.random()) if noise else bad
                cand.append((score, word + [L], T))
        cand.sort(key=lambda t: t[0])
        frontier = cand[:beam]
        log(f"  prefix {w}: fewest suffix-completable states {frontier[0][0]:.0f}, {len(cand)} candidates")
    return None


def mirror_letters(h: int) -> list[int]:
    out = []
    for L in range(1 << h):
        if all(((L >> i) & 1) == ((L >> (h - 1 - i)) & 1) for i in range(h)):
            out.append(L)
    return out


def step_all(S: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Successor sets for every letter at once: shape (letters, n, n)."""
    return (S[None, :, :, None] & valid).any(axis=1)


def lookahead(S: np.ndarray, valid: np.ndarray, good: np.ndarray, depth: int):
    """Exact search: a letter word of length <= depth from S whose reachable set
    avoids `good` entirely (returns the word), else None."""
    T = step_all(S, valid)
    bad = (T & good[None]).sum(axis=(1, 2))
    hits = np.nonzero(bad == 0)[0]
    if len(hits):
        return [int(hits[0])]
    if depth <= 1:
        return None
    order = np.argsort(bad)
    for L in order:
        if not T[L].any():
            return [int(L)]
        sub = lookahead(T[L], valid, good, depth - 1)
        if sub is not None:
            return [int(L)] + sub
    return None


def beam_prefix_la(h: int, valid: np.ndarray, suffix: list[int], beam: int, max_prefix: int,
                   rng: random.Random, log=print, noise: float = 0.0, la_depth: int = 2,
                   la_top: int = 200, la_from: int | None = None):
    """beam_prefix with an exact lookahead of `la_depth` columns applied to the
    `la_top` best frontier sets at prefix widths >= la_from (default: the last
    la_depth widths), so the final collapse is found exactly, not greedily."""
    n = 1 << (h + 2)
    letters = list(range(1 << h))
    good = good_set(valid, suffix)
    start = np.ones((n, n), dtype=bool)
    frontier = [(int((start & good).sum()), [], start)]
    if la_from is None:
        la_from = max_prefix - la_depth
    for w in range(1, max_prefix + 1):
        cand = []
        seen = set()
        for _, word, S in frontier:
            T = step_all(S, valid)
            bads = (T & good[None]).sum(axis=(1, 2))
            for L in letters:
                bad = int(bads[L])
                if bad == 0:
                    return word + [L]
                key = T[L].tobytes()
                if key in seen:
                    continue
                seen.add(key)
                score = bad * (1.0 + noise * rng.random()) if noise else bad
                cand.append((score, word + [L], T[L]))
        cand.sort(key=lambda t: t[0])
        frontier = cand[:beam]
        log(f"  prefix {w}: fewest suffix-completable states {frontier[0][0]:.0f}, {len(cand)} candidates")
        if w >= la_from:
            remaining = max_prefix - w
            d = min(la_depth, remaining)
            if d >= 1:
                for _, word, S in frontier[:la_top]:
                    ext = lookahead(S, valid, good, d)
                    if ext is not None:
                        return word + ext
                log(f"    lookahead depth {d} on top {min(la_top, len(frontier))}: none")
    return None
