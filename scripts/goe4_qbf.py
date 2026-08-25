#!/usr/bin/env python3
"""2QBF search for a four-row-live Garden of Eden orphan (LIFE-C001).

For window height H = 4 + 2*d (middle four rows free, d dead rows above and
below) and width w, generates the QDIMACS instance

    exists P (4*w pattern bits)
    forall X ((H+2)*(w+2) preimage bits)
    exists aux:   "X is not a preimage patch of the window"

which is TRUE iff an orphan of width <= w exists with this shape (a narrower
orphan padded with specified dead columns is still an orphan, so the answer
is monotone in w). FALSE is a rigorous bounded negative: no such orphan with
width <= w. By Wade's 2023 theorem, d = 0 must be FALSE for every width —
the built-in validation.

Life-step biconditionals are encoded per image cell with the 512 blocked
neighbourhood assignments (as in scripts/preimage_sat.py); a found pattern is
decoded from the solver's outermost existential assignment and cross-checked
with preimage_sat before being reported.

Solver: CAQE (exit 10 = TRUE/orphan, 20 = FALSE/none). Build notes in the
research log; pass --caqe to run and decode in one step, otherwise only the
.qdimacs file is written.
"""

from __future__ import annotations

import argparse
import itertools
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

NEIGH = [(dr, dc) for dr in (0, 1, 2) for dc in (0, 1, 2)]


def life_out(bits: tuple[int, ...]) -> int:
    centre = bits[4]
    s = sum(bits) - centre
    return 1 if s == 3 or (s == 2 and centre == 1) else 0


def _quine_mccluskey(minterms: list[int], n: int) -> list[tuple[int, int]]:
    """Prime implicants of the given minterms over n variables, as
    (value, mask) pairs where mask bits are the DON'T-CARE positions.
    Returns a greedy cover of all minterms (not guaranteed minimum)."""
    current = {(m, 0) for m in minterms}
    primes: set[tuple[int, int]] = set()
    while current:
        merged: set[tuple[int, int]] = set()
        used: set[tuple[int, int]] = set()
        by_mask: dict[int, list[tuple[int, int]]] = {}
        for term in current:
            by_mask.setdefault(term[1], []).append(term)
        for _, terms in by_mask.items():
            for i, (v1, m1) in enumerate(terms):
                for v2, m2 in terms[i + 1 :]:
                    diff = v1 ^ v2
                    if diff.bit_count() == 1:
                        merged.add((v1 & ~diff, m1 | diff))
                        used.add((v1, m1))
                        used.add((v2, m2))
        primes.update(current - used)
        current = merged
    # Greedy set cover.
    def covers(prime: tuple[int, int], m: int) -> bool:
        value, mask = prime
        return (m & ~mask) == value

    uncovered = set(minterms)
    cover: list[tuple[int, int]] = []
    while uncovered:
        best = max(primes, key=lambda p: sum(1 for m in uncovered if covers(p, m)))
        cover.append(best)
        uncovered = {m for m in uncovered if not covers(best, m)}
    return cover


def _life_covers() -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """(ON-cover, OFF-cover) of the 9-input Life function, minterm bit k =
    NEIGH[k] cell."""
    on = []
    off = []
    for m in range(512):
        bits = tuple((m >> k) & 1 for k in range(9))
        (on if life_out(bits) else off).append(m)
    on_cover = _quine_mccluskey(on, 9)
    off_cover = _quine_mccluskey(off, 9)
    for m in range(512):
        in_on = any((m & ~mask) == value for value, mask in on_cover)
        in_off = any((m & ~mask) == value for value, mask in off_cover)
        assert in_on == (m in set(on)) and in_off == (m in set(off)), m
    return on_cover, off_cover


_ON_COVER, _OFF_COVER = _life_covers()


def generate(dead_rows: int, width: int) -> tuple[str, dict[tuple[int, int], int]]:
    """Return (qdimacs text, pattern-var map (row, col) -> var)."""
    height = 4 + 2 * dead_rows
    ph, pw = height + 2, width + 2

    next_var = 1

    def fresh() -> int:
        nonlocal next_var
        v = next_var
        next_var += 1
        return v

    p_var = {(i, j): fresh() for i in range(4) for j in range(width)}
    x_var = {(r, c): fresh() for r in range(ph) for c in range(pw)}
    t_var = {(i, j): fresh() for i in range(height) for j in range(width)}
    # diff vars only for the middle rows; border rows use t directly.
    diff_var = {(i, j): fresh() for i in range(4) for j in range(width)}

    clauses: list[list[int]] = []

    # t <-> Life(neighbourhood), via prime-implicant covers:
    #   ON-term D (t | -D gives t <- ... wait: D -> t):  clause (-D | t)
    #   OFF-term E (E -> -t):                            clause (-E | -t)
    # Together these fix t for every assignment (covers partition all 512).
    for i in range(height):
        for j in range(width):
            t = t_var[(i, j)]
            cell_vars = [x_var[(i + dr, j + dc)] for dr, dc in NEIGH]

            def term_clause(value: int, mask: int, tail: int) -> list[int]:
                lits = []
                for k in range(9):
                    if mask & (1 << k):
                        continue
                    lits.append(-cell_vars[k] if value & (1 << k) else cell_vars[k])
                lits.append(tail)
                return lits

            for value, mask in _ON_COVER:
                clauses.append(term_clause(value, mask, t))
            for value, mask in _OFF_COVER:
                clauses.append(term_clause(value, mask, -t))

    mismatch: list[int] = []
    for i in range(height):
        for j in range(width):
            t = t_var[(i, j)]
            if dead_rows <= i < dead_rows + 4:
                p = p_var[(i - dead_rows, j)]
                d = diff_var[(i - dead_rows, j)]
                clauses.append([-d, t, p])
                clauses.append([-d, -t, -p])
                clauses.append([d, -t, p])
                clauses.append([d, t, -p])
                mismatch.append(d)
            else:
                # border row must be dead; any live output is a mismatch.
                mismatch.append(t)
    clauses.append(mismatch)

    lines = [f"p cnf {next_var - 1} {len(clauses)}"]
    lines.append("e " + " ".join(str(v) for v in sorted(p_var.values())) + " 0")
    lines.append("a " + " ".join(str(v) for v in sorted(x_var.values())) + " 0")
    aux = sorted(t_var.values()) + sorted(diff_var.values())
    lines.append("e " + " ".join(str(v) for v in aux) + " 0")
    lines.extend(" ".join(str(l) for l in c) + " 0" for c in clauses)
    return "\n".join(lines) + "\n", p_var


def generate_dual(dead_rows: int, width: int, symmetry: bool = False) -> str:
    """Dual instance: forall P exists X, aux: F(X) = window(P).
    TRUE  <=> every four-row pattern of width w has a preimage patch
          <=> no orphan of this shape with width <= w.
    FALSE <=> an orphan exists (the solver's falsifying P is the witness).

    With symmetry=True the preimage obligation is restricted to lex-leaders
    of the orbit under the strip-preserving symmetry group {column reversal,
    row flip, 180-degree rotation}: orphan-hood is invariant under these, so
    the answer is unchanged while the effective forall-space shrinks up to 4x.
    Implemented as (lexleq(P, g(P)) for all g) -> (F(X) = window(P)), with
    fully biconditional lex chains so the inner existential cannot cheat."""
    height = 4 + 2 * dead_rows
    ph, pw = height + 2, width + 2

    next_var = 1

    def fresh() -> int:
        nonlocal next_var
        v = next_var
        next_var += 1
        return v

    p_var = {(i, j): fresh() for i in range(4) for j in range(width)}
    x_var = {(r, c): fresh() for r in range(ph) for c in range(pw)}
    t_var = {(i, j): fresh() for i in range(height) for j in range(width)}

    clauses: list[list[int]] = []
    for i in range(height):
        for j in range(width):
            t = t_var[(i, j)]
            cell_vars = [x_var[(i + dr, j + dc)] for dr, dc in NEIGH]

            def term_clause(value: int, mask: int, tail: int) -> list[int]:
                lits = []
                for k in range(9):
                    if mask & (1 << k):
                        continue
                    lits.append(-cell_vars[k] if value & (1 << k) else cell_vars[k])
                lits.append(tail)
                return lits

            for value, mask in _ON_COVER:
                clauses.append(term_clause(value, mask, t))
            for value, mask in _OFF_COVER:
                clauses.append(term_clause(value, mask, -t))

    # Optional symmetry breaking: L_g <-> lexleq(P, g(P)) for the three
    # non-identity strip symmetries; the preimage obligation below is then
    # guarded by (L_1 & L_2 & L_3).
    guard: list[int] = []
    aux_extra: list[int] = []
    if symmetry:
        order = [(i, j) for i in range(4) for j in range(width)]
        symmetries = [
            lambda i, j: (i, width - 1 - j),
            lambda i, j: (3 - i, j),
            lambda i, j: (3 - i, width - 1 - j),
        ]
        for g in symmetries:
            xs = [p_var[pos] for pos in order]
            ys = [p_var[g(*pos)] for pos in order]
            m = len(xs)
            e = {0: None}
            big_l = fresh()
            aux_extra.append(big_l)
            vs: list[int] = []
            prev_e: int | None = None
            for k in range(1, m + 1):
                xk, yk = xs[k - 1], ys[k - 1]
                # v_k = prefix-equal(k-1) & x_k & -y_k
                v = fresh()
                aux_extra.append(v)
                if prev_e is not None:
                    clauses.append([-v, prev_e])
                clauses.append([-v, xk])
                clauses.append([-v, -yk])
                vs.append(v)
                # L -> not v_k  (expanded so L is refuted by any actual violation)
                lead = [-big_l, -xk, yk] if prev_e is None else [-big_l, -prev_e, -xk, yk]
                clauses.append(lead)
                if k < m:
                    ek = fresh()
                    aux_extra.append(ek)
                    if prev_e is not None:
                        clauses.append([-ek, prev_e])
                    clauses.append([-ek, -xk, yk])
                    clauses.append([-ek, xk, -yk])
                    if prev_e is not None:
                        clauses.append([ek, -prev_e, xk, yk])
                        clauses.append([ek, -prev_e, -xk, -yk])
                    else:
                        clauses.append([ek, xk, yk])
                        clauses.append([ek, -xk, -yk])
                    prev_e = ek
            # -L -> some violation
            clauses.append([big_l] + vs)
            guard.append(-big_l)
            del e

    # F(X) = window(P): every output equals its window value (for lex-leaders).
    for i in range(height):
        for j in range(width):
            t = t_var[(i, j)]
            if dead_rows <= i < dead_rows + 4:
                p = p_var[(i - dead_rows, j)]
                clauses.append(guard + [-t, p])
                clauses.append(guard + [t, -p])
            else:
                clauses.append(guard + [-t])

    lines = [f"p cnf {next_var - 1} {len(clauses)}"]
    lines.append("a " + " ".join(str(v) for v in sorted(p_var.values())) + " 0")
    aux = sorted(x_var.values()) + sorted(t_var.values()) + aux_extra
    lines.append("e " + " ".join(str(v) for v in aux) + " 0")
    lines.extend(" ".join(str(l) for l in c) + " 0" for c in clauses)
    return "\n".join(lines) + "\n"


def decode_pattern(
    output: str, p_var: dict[tuple[int, int], int], dead_rows: int, width: int
) -> list[list[int]]:
    """Window raster (height x width) from CAQE's --qdo V-lines."""
    assign: dict[int, int] = {}
    for line in output.splitlines():
        if line.startswith("V"):
            for tok in line.split()[1:]:
                lit = int(tok)
                if lit != 0:
                    assign[abs(lit)] = 1 if lit > 0 else 0
    height = 4 + 2 * dead_rows
    window = [[0] * width for _ in range(height)]
    for (i, j), v in p_var.items():
        window[dead_rows + i][j] = assign.get(v, 0)
    return window


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dead-rows", type=int, default=1)
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--out", type=Path, help="write QDIMACS here (default: temp name)")
    parser.add_argument("--caqe", type=Path, help="CAQE binary; solve and decode")
    parser.add_argument("--timeout", type=int, default=3600, help="solver timeout seconds")
    parser.add_argument(
        "--dual",
        action="store_true",
        help="forall-P/exists-X form: TRUE = no orphan with width <= w, FALSE = orphan exists",
    )
    parser.add_argument(
        "--symmetry",
        action="store_true",
        help="dual form only: restrict the forall to lex-leaders of the strip symmetry group",
    )
    args = parser.parse_args()

    if args.dual:
        text = generate_dual(args.dead_rows, args.width, args.symmetry)
        out = args.out or Path(f"goe4_dual_d{args.dead_rows}_w{args.width}.qdimacs")
        out.write_text(text, encoding="ascii", newline="\n")
        n_vars, n_clauses = text.split("\n", 1)[0].split()[2:4]
        print(f"wrote {out}: {n_vars} vars, {n_clauses} clauses (dual form)")
        if not args.caqe:
            return 0
        proc = subprocess.run(
            [str(args.caqe), str(out)], capture_output=True, text=True, timeout=args.timeout
        )
        if proc.returncode == 10:
            print(
                f"TRUE (dual): every pattern has a preimage — no orphan of height "
                f"{4 + 2 * args.dead_rows} (dead rows {args.dead_rows}) with width <= {args.width}"
            )
            return 20
        if proc.returncode == 20:
            print("FALSE (dual): an orphan of width <= {} exists!".format(args.width))
            return 10
        print(f"solver exit {proc.returncode}; stdout tail:\n{proc.stdout[-400:]}")
        return proc.returncode

    text, p_var = generate(args.dead_rows, args.width)
    out = args.out or Path(f"goe4_d{args.dead_rows}_w{args.width}.qdimacs")
    out.write_text(text, encoding="ascii", newline="\n")
    n_vars, n_clauses = text.split("\n", 1)[0].split()[2:4]
    print(f"wrote {out}: {n_vars} vars, {n_clauses} clauses "
          f"(height {4 + 2 * args.dead_rows}, width {args.width})")
    if not args.caqe:
        return 0

    proc = subprocess.run(
        [str(args.caqe), "--qdo", str(out)],
        capture_output=True,
        text=True,
        timeout=args.timeout,
    )
    if proc.returncode == 20:
        print(f"FALSE: no orphan of height {4 + 2 * args.dead_rows} "
              f"(dead rows {args.dead_rows}) with width <= {args.width}")
        return 20
    if proc.returncode != 10:
        print(f"solver exit {proc.returncode}; stdout tail:\n{proc.stdout[-500:]}")
        return proc.returncode

    window = decode_pattern(proc.stdout, p_var, args.dead_rows, args.width)
    print("TRUE: orphan candidate window:")
    for row in window:
        print("".join("1" if v else "0" for v in row))

    import preimage_sat as ps

    has, _ = ps.check_window(window)
    if has:
        print("CROSS-CHECK FAILED: preimage_sat found a preimage — encoding bug, distrust")
        return 1
    print("CROSS-CHECK PASSED: preimage_sat confirms the window is an orphan. "
          "A four-row-live Garden of Eden exists.")
    return 10


if __name__ == "__main__":
    raise SystemExit(main())
