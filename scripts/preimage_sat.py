#!/usr/bin/env python3
"""One-step Life preimage SAT checker (local orphan test).

A fully specified h x w window is an ORPHAN iff no (h+2) x (w+2) preimage
patch maps onto it under one B3/S23 step (an image cell depends only on its
3x3 preimage neighbourhood, so the +1 margin is exact). By compactness, any
configuration containing an orphan as a sub-window is a Garden of Eden.

Encoding: one Boolean variable per preimage cell; for every image cell, all
3x3 neighbourhood assignments producing the wrong output are blocked as
9-literal clauses (140 alive-producing / 372 dead-producing assignments).
Deliberately naive and bulletproof; window sizes of interest stay small.

Requires python-sat (`pip install python-sat`) — not part of the repository's
stdlib-only validation path; tests skip when pysat is absent.

CLI:
  preimage_sat.py check WINDOW_FILE     # raster of 0/1 (also ./o), all cells specified
  preimage_sat.py validate --height H --width W   # exhaustive cross-check vs brute force
"""

from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

NEIGH = [(dr, dc) for dr in (0, 1, 2) for dc in (0, 1, 2)]  # (1,1) is the centre


def life_out(bits: tuple[int, ...]) -> int:
    """Next state of the centre given the 9 neighbourhood bits in NEIGH order."""
    centre = bits[4]
    s = sum(bits) - centre
    return 1 if s == 3 or (s == 2 and centre == 1) else 0


# For each image value v, the neighbourhood assignments that must be blocked.
_BLOCKED: dict[int, list[tuple[int, ...]]] = {0: [], 1: []}
for _bits in itertools.product((0, 1), repeat=9):
    _BLOCKED[1 - life_out(_bits)].append(_bits)


def parse_window(text: str) -> list[list[int]]:
    rows: list[list[int]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        row = []
        for ch in line:
            if ch in "1oO*":
                row.append(1)
            elif ch in "0.b":
                row.append(0)
            else:
                raise ValueError(f"unexpected raster character {ch!r}")
        rows.append(row)
    if not rows or len({len(r) for r in rows}) != 1:
        raise ValueError("window must be a non-empty rectangle")
    return rows


def build_clauses(window: list[list[int]]) -> tuple[list[list[int]], int, int]:
    """CNF over preimage vars; var id of preimage cell (r, c) is r*(w+2)+c+1."""
    h, w = len(window), len(window[0])
    pw = w + 2

    def var(r: int, c: int) -> int:
        return r * pw + c + 1

    clauses: list[list[int]] = []
    for i in range(h):
        for j in range(w):
            cell_vars = [var(i + dr, j + dc) for dr, dc in NEIGH]
            for assignment in _BLOCKED[window[i][j]]:
                clauses.append(
                    [-v if bit else v for v, bit in zip(cell_vars, assignment)]
                )
    return clauses, h + 2, pw


def check_window(
    window: list[list[int]], solver_name: str = "g3"
) -> tuple[bool, list[list[int]] | None]:
    """Return (has_preimage, preimage_patch_or_None)."""
    from pysat.solvers import Solver

    clauses, ph, pw = build_clauses(window)
    with Solver(name=solver_name, bootstrap_with=clauses) as solver:
        if not solver.solve():
            return False, None
        model = set(lit for lit in solver.get_model() if lit > 0)
        patch = [[1 if (r * pw + c + 1) in model else 0 for c in range(pw)] for r in range(ph)]
        return True, patch


def step_patch(patch: list[list[int]]) -> list[list[int]]:
    """Image of the patch interior (one cell smaller on every side)."""
    ph, pw = len(patch), len(patch[0])
    return [
        [
            life_out(tuple(patch[i + dr][j + dc] for dr, dc in NEIGH))
            for j in range(pw - 2)
        ]
        for i in range(ph - 2)
    ]


def verify_patch(window: list[list[int]], patch: list[list[int]]) -> bool:
    return step_patch(patch) == window


def brute_force_images(h: int, w: int) -> set[tuple[int, ...]]:
    """All achievable h x w image windows, flattened row-major. Tiny sizes only."""
    ph, pw = h + 2, w + 2
    n = ph * pw
    if n > 22:
        raise ValueError("brute force limited to preimage areas <= 22 cells")
    images: set[tuple[int, ...]] = set()
    for bits in range(1 << n):
        patch = [[(bits >> (r * pw + c)) & 1 for c in range(pw)] for r in range(ph)]
        images.add(tuple(itertools.chain.from_iterable(step_patch(patch))))
    return images


def exhaustive_validate(h: int, w: int, solver_name: str = "g3") -> tuple[int, int]:
    """Cross-check SAT answers against brute force for every h x w window.

    Returns (mismatches, orphans). Both are expected to be 0 at tiny sizes.
    """
    images = brute_force_images(h, w)
    mismatches = orphans = 0
    for bits in range(1 << (h * w)):
        window = [[(bits >> (i * w + j)) & 1 for j in range(w)] for i in range(h)]
        flat = tuple(itertools.chain.from_iterable(window))
        expected = flat in images
        got, patch = check_window(window, solver_name)
        if got != expected:
            mismatches += 1
        if got and not verify_patch(window, patch):
            mismatches += 1
        if not got:
            orphans += 1
    return mismatches, orphans


def format_raster(grid: list[list[int]]) -> str:
    return "\n".join("".join("1" if v else "0" for v in row) for row in grid)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check", help="preimage-check a fully specified window")
    p_check.add_argument("window", type=Path)
    p_check.add_argument("--solver", default="g3")

    p_val = sub.add_parser("validate", help="exhaustive cross-check vs brute force")
    p_val.add_argument("--height", type=int, required=True)
    p_val.add_argument("--width", type=int, required=True)
    p_val.add_argument("--solver", default="g3")

    args = parser.parse_args()

    if args.cmd == "check":
        window = parse_window(args.window.read_text(encoding="utf-8"))
        has_preimage, patch = check_window(window, args.solver)
        if has_preimage:
            assert verify_patch(window, patch)
            print("SAT: preimage exists; verified patch:")
            print(format_raster(patch))
            return 0
        print("UNSAT: window is an ORPHAN (no one-step preimage patch)")
        return 2

    mismatches, orphans = exhaustive_validate(args.height, args.width, args.solver)
    total = 1 << (args.height * args.width)
    print(
        f"windows {total}, mismatches {mismatches}, orphans {orphans} "
        f"({'OK' if mismatches == 0 else 'ENCODING BUG'})"
    )
    return 0 if mismatches == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
