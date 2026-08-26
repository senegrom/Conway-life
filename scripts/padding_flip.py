#!/usr/bin/env python3
"""Flip-point search for the Salo-Törmä optimal padding constant (LIFE-F001).

For a rectangular pattern P, pad^c(P) is P surrounded by c rings of specified
dead cells, and "admits a preimage" means a patch on the domain enlarged by
the radius-1 margin maps onto it exactly (scripts/preimage_sat.py semantics,
matching Section 2 of arXiv:1912.00692). Preimage existence is anti-monotone
in c (a preimage of a thicker padding restricts to one of a thinner), so each
P has a single flip point

    f(P) = least c >= 0 with pad^c(P) admitting NO preimage  (infinity if none),

and Theorem 5 of the paper gives f(P) in {0,1,2,3,4, infinity}: if pad^4(P)
admits a preimage, conf_0(P) has a global preimage, hence every padding does.
The optimal constant asked for in Salo's Q28820954 equals max finite f(P).
Known bound: >= 1. **Any pattern with f(P) >= 2 improves the lower bound.**

Classification per pattern: check c = 0..4; SAT at c=4 classifies as infinity
(by the theorem — spot-check this with the `sanity` subcommand, which verifies
SAT@4 => SAT@5,6 on random patterns; a violation would mean an encoding bug).

Sweeps deduplicate by the 8 rectangle symmetries (and transpose for squares).
Requires python-sat.
"""

from __future__ import annotations

import argparse
import itertools
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preimage_sat as ps


def pad_window(rows: list[list[int]], c: int) -> list[list[int]]:
    if c == 0:
        return rows
    w = len(rows[0])
    blank = [0] * (w + 2 * c)
    out = [blank[:] for _ in range(c)]
    for row in rows:
        out.append([0] * c + row + [0] * c)
    out.extend(blank[:] for _ in range(c))
    return out


def flip_point(rows: list[list[int]], max_c: int = 4) -> int | None:
    """f(P) if <= max_c, else None (= infinity by Theorem 5 when max_c >= 4)."""
    for c in range(max_c + 1):
        has, _ = ps.check_window(pad_window(rows, c))
        if not has:
            return c
    return None


def bits_to_rows(bits: int, h: int, w: int) -> list[list[int]]:
    return [[(bits >> (i * w + j)) & 1 for j in range(w)] for i in range(h)]


def symmetry_orbit(bits: int, h: int, w: int) -> list[int]:
    """All D2 (or D4 for squares) images of the pattern, as bit codes."""
    rows = bits_to_rows(bits, h, w)
    variants = []
    mats = [rows, [r[::-1] for r in rows], rows[::-1], [r[::-1] for r in rows[::-1]]]
    if h == w:
        t = [list(col) for col in zip(*rows)]
        mats += [t, [r[::-1] for r in t], t[::-1], [r[::-1] for r in t[::-1]]]
    for m in mats:
        code = 0
        for i in range(h):
            for j in range(w):
                code |= m[i][j] << (i * w + j)
        variants.append(code)
    return variants


def sweep(h: int, w: int, report_every: float, show_f1: bool) -> None:
    total = 1 << (h * w)
    counts: dict[object, int] = {}
    witnesses: dict[int, int] = {}
    seen_canon = 0
    t0 = time.perf_counter()
    last = t0
    for bits in range(1, total):
        if min(symmetry_orbit(bits, h, w)) != bits:
            continue
        seen_canon += 1
        rows = bits_to_rows(bits, h, w)
        f = flip_point(rows)
        key = f if f is not None else "inf"
        counts[key] = counts.get(key, 0) + 1
        if f is not None and f >= 1 and f not in witnesses:
            witnesses[f] = bits
            if f >= 2 or show_f1:
                print(f"WITNESS f={f} for {h}x{w} pattern:")
                for row in rows:
                    print("".join(map(str, row)))
        if f is not None and f >= 2:
            print(f"*** f={f} >= 2: LOWER BOUND IMPROVEMENT CANDIDATE (bits={bits}) ***")
            for row in rows:
                print("".join(map(str, row)))
        now = time.perf_counter()
        if now - last > report_every:
            print(f"{h}x{w}: {seen_canon} canonical patterns, counts {counts}", flush=True)
            last = now
    print(
        f"DONE {h}x{w}: {seen_canon} canonical patterns (of {total - 1}), "
        f"flip-point counts {counts}, {time.perf_counter() - t0:.1f}s"
    )


def sanity(samples: int, h: int, w: int, seed: int) -> None:
    rng = random.Random(seed)
    checked = 0
    for _ in range(samples):
        bits = rng.randrange(1, 1 << (h * w))
        rows = bits_to_rows(bits, h, w)
        if flip_point(rows) is None:
            for c in (5, 6):
                has, _ = ps.check_window(pad_window(rows, c))
                if not has:
                    print(f"THEOREM VIOLATION at c={c} (encoding bug!) bits={bits}")
                    return
            checked += 1
    print(f"sanity OK: {checked} patterns with SAT@4 also SAT@5,6 (of {samples} sampled)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_sweep = sub.add_parser("sweep")
    p_sweep.add_argument("--height", type=int, required=True)
    p_sweep.add_argument("--width", type=int, required=True)
    p_sweep.add_argument("--report-every", type=float, default=30.0)
    p_sweep.add_argument("--show-f1", action="store_true")
    p_san = sub.add_parser("sanity")
    p_san.add_argument("--samples", type=int, default=300)
    p_san.add_argument("--height", type=int, default=4)
    p_san.add_argument("--width", type=int, default=4)
    p_san.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.cmd == "sweep":
        sweep(args.height, args.width, args.report_every, args.show_f1)
    else:
        sanity(args.samples, args.height, args.width, args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
