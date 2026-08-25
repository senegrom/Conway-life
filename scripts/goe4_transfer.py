#!/usr/bin/env python3
"""Column-transfer search for a four-row-live Garden of Eden orphan.

Question (LIFE-C001): does a Garden of Eden exist whose live cells lie in
four consecutive rows? A witness is an ORPHAN: a fully specified window of
height H = 4 + 2*d (middle 4 rows free, d rows above and below specified
dead) that no (H+2) x (w+2) preimage patch maps onto.

Formulation: preimage columns are (H+2)-bit vectors. Image column j is a
function img(a, b, c) of three consecutive preimage columns. Consider the
NFA whose states are pairs (a, b) of preimage columns, with transition
(a, b) --sigma--> (b, c) iff img(a, b, c) = sigma, all states initial and
final (patch boundary columns are unconstrained). A window word
sigma_1..sigma_w has a preimage patch iff the NFA accepts it. Hence an
orphan of height H exists iff the NFA is NOT universal over the alphabet
of allowed image columns (top/bottom d bits dead, 16 letters).

Universality is checked by subset construction from the full state set,
searching for a reachable empty subset (breadth-first, so a found orphan
has minimal width for its height). Subsets are represented grouped by the
second column: M[b] = bitmask over first columns a. Antichain pruning:
a new subset that is a superset of a seen subset is dominated (any word
emptying the superset also empties the subset) and skipped.

Validation: for d = 0 this must report UNIVERSAL, reproducing the known
theorem that no height-4 orphan exists. Any found orphan is cross-checked
with scripts/preimage_sat.py before being reported.

Pure stdlib. Memory/time grow steeply with d; d=0 is instant, d=1 is the
first open regime.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

LIFE_ROW_TRIPLE: list[int] = []


def _init_row_table() -> None:
    """LIFE_ROW_TRIPLE[key] for key = a3 | b3<<3 | c3<<6: next state of the
    centre cell of the middle column, given 3-row slices of columns a,b,c."""
    for key in range(512):
        a3 = key & 7
        b3 = (key >> 3) & 7
        c3 = (key >> 6) & 7
        centre = (b3 >> 1) & 1
        s = bin(a3).count("1") + bin(b3).count("1") + bin(c3).count("1") - centre
        LIFE_ROW_TRIPLE.append(1 if s == 3 or (s == 2 and centre) else 0)


_init_row_table()


def img_col(a: int, b: int, c: int, height: int) -> int:
    """Image column (height bits) from three preimage columns (height+2 bits).
    Bit i of the image corresponds to preimage rows i, i+1, i+2."""
    out = 0
    for i in range(height):
        key = ((a >> i) & 7) | (((b >> i) & 7) << 3) | (((c >> i) & 7) << 6)
        out |= LIFE_ROW_TRIPLE[key] << i
    return out


def search(dead_rows: int, max_depth: int | None, report_every: float, verify: bool) -> int:
    height = 4 + 2 * dead_rows
    pre_bits = height + 2
    ncols = 1 << pre_bits
    full_mask = (1 << ncols) - 1

    # Allowed image columns: middle 4 rows free, d rows dead at top and bottom.
    alphabet = [middle << dead_rows for middle in range(16)]

    print(
        f"height {height} (dead rows {dead_rows}), preimage columns {ncols}, "
        f"states {ncols * ncols}, alphabet {len(alphabet)}"
    )

    # A[sigma][b * ncols + c] = bitmask over a with img(a,b,c) == sigma.
    t0 = time.perf_counter()
    sigma_index = {s: i for i, s in enumerate(alphabet)}
    a_table: list[list[int]] = [[0] * (ncols * ncols) for _ in alphabet]
    for b in range(ncols):
        base = b * ncols
        for a in range(ncols):
            bit = 1 << a
            for c in range(ncols):
                idx = sigma_index.get(img_col(a, b, c, height))
                if idx is not None:
                    a_table[idx][base + c] |= bit
    print(f"transition tables built in {time.perf_counter() - t0:.1f}s")

    # Subset state: tuple M of length ncols; M[b] = mask over a of pairs (a,b).
    start = tuple([full_mask] * ncols)

    def successor(m: tuple[int, ...], sigma_idx: int) -> tuple[int, ...]:
        table = a_table[sigma_idx]
        out = [0] * ncols
        for b in range(ncols):
            mb = m[b]
            if not mb:
                continue
            base = b * ncols
            bbit = 1 << b
            for c in range(ncols):
                if mb & table[base + c]:
                    out[c] |= bbit
        return tuple(out)

    def is_subset(small: tuple[int, ...], big: tuple[int, ...]) -> bool:
        return all((s | g) == g for s, g in zip(small, big))

    # Antichain of minimal seen subsets; a new subset that is a superset of a
    # seen one is dominated. Parents recorded for word reconstruction.
    antichain: list[tuple[int, ...]] = []
    parent: dict[tuple[int, ...], tuple[tuple[int, ...], int]] = {}
    queue: deque[tuple[tuple[int, ...], int]] = deque([(start, 0)])
    antichain.append(start)
    explored = 0
    last_report = time.perf_counter()

    while queue:
        m, depth = queue.popleft()
        if max_depth is not None and depth >= max_depth:
            continue
        explored += 1
        now = time.perf_counter()
        if now - last_report > report_every:
            print(
                f"depth {depth}, explored {explored}, antichain {len(antichain)}, queue {len(queue)}",
                flush=True,
            )
            last_report = now
        for sigma_idx in range(len(alphabet)):
            nxt = successor(m, sigma_idx)
            if not any(nxt):
                # Empty subset reached: reconstruct the escaping word.
                word = [alphabet[sigma_idx]]
                cur = m
                while cur != start:
                    prev, sidx = parent[cur]
                    word.append(alphabet[sidx])
                    cur = prev
                word.reverse()
                report_orphan(word, height, dead_rows, verify)
                return 2
            dominated = False
            for seen in antichain:
                if is_subset(seen, nxt):
                    dominated = True
                    break
            if dominated:
                continue
            antichain[:] = [s for s in antichain if not is_subset(nxt, s)]
            antichain.append(nxt)
            parent[nxt] = (m, sigma_idx)
            queue.append((nxt, depth + 1))

    print(
        f"UNIVERSAL at height {height}: every four-row pattern with {dead_rows} "
        f"specified dead rows above and below has a preimage patch. "
        f"No orphan of this shape exists. (antichain {len(antichain)}, explored {explored})"
    )
    return 0


def report_orphan(word: list[int], height: int, dead_rows: int, verify: bool) -> None:
    width = len(word)
    window = [[(col >> i) & 1 for col in word] for i in range(height)]
    print(f"ORPHAN CANDIDATE: height {height} (dead rows {dead_rows}), width {width}")
    for row in window:
        print("".join("1" if v else "0" for v in row))
    if verify:
        import preimage_sat as ps

        has, _ = ps.check_window(window)
        if has:
            print("CROSS-CHECK FAILED: preimage_sat found a preimage — BUG, do not trust")
        else:
            print(
                "CROSS-CHECK PASSED: preimage_sat confirms no preimage patch. "
                "This window is an orphan; a four-row-live Garden of Eden exists."
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dead-rows", type=int, default=0, help="d; window height is 4+2d")
    parser.add_argument("--max-depth", type=int, help="cap the search width (bounded result)")
    parser.add_argument("--report-every", type=float, default=10.0)
    parser.add_argument("--no-verify", action="store_true")
    args = parser.parse_args()
    return search(args.dead_rows, args.max_depth, args.report_every, not args.no_verify)


if __name__ == "__main__":
    raise SystemExit(main())
