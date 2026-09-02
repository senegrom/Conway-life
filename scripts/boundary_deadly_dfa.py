#!/usr/bin/env python3
"""Straight-segment deadliness for ALL lengths via subset construction.

Reads a boundary word one position at a time: letter = (d0[x], d1[x]).
NFA state = (d2[x-1], d2[x], d3[x-1], d3[x]) plus the deterministic memory
of the last two (d0, d1) letters. On reading position x+1 the automaton
chooses (d2[x+1], d3[x+1]) and enforces R1-dead and R2-dead at x (whose
3-windows are now known). The R1-only automaton ignores d3 and R2.

DFA state = (last two letters, subset of joint states, subset of R1
states). A reachable DFA state with non-empty R1 subset and empty joint
subset is a level-2 deadly segment (free ends: both automata start with
all states allowed). BFS over reachable DFA states decides existence for
segments of every length at once.
"""

from __future__ import annotations

import itertools
from collections import deque


def life(c: int, n: int) -> int:
    return 1 if n == 3 or (n == 2 and c == 1) else 0


def step(letters2, joint_mask, r1_mask, letter):
    """Apply one position. letters2 = ((d0[x-1],d1[x-1]), (d0[x],d1[x]));
    letter = (d0[x+1], d1[x+1]). Constraints at x."""
    (a0, a1), (b0, b1) = letters2
    c0, c1 = letter
    d0win = a0 + b0 + c0
    d1win = a1 + b1 + c1
    new_joint = 0
    new_r1 = 0
    for s in range(16):
        if not (joint_mask >> s) & 1:
            continue
        p2, q2, p3, q3 = s & 1, (s >> 1) & 1, (s >> 2) & 1, (s >> 3) & 1
        for e2, e3 in itertools.product((0, 1), repeat=2):
            r1ok = life(b1, d0win + a1 + c1 + p2 + q2 + e2) == 0
            r2ok = life(q2, d1win + p2 + e2 + p3 + q3 + e3) == 0
            if r1ok and r2ok:
                new_joint |= 1 << (q2 | (e2 << 1) | (q3 << 2) | (e3 << 3))
    for s in range(4):
        if not (r1_mask >> s) & 1:
            continue
        p2, q2 = s & 1, (s >> 1) & 1
        for e2 in (0, 1):
            if life(b1, d0win + a1 + c1 + p2 + q2 + e2) == 0:
                new_r1 |= 1 << (q2 | (e2 << 1))
    return ((b0, b1), (c0, c1)), new_joint, new_r1


def main() -> int:
    letters = [(a, b) for a in (0, 1) for b in (0, 1)]
    start = []
    for l1 in letters:
        for l2 in letters:
            start.append(((l1, l2), 0xFFFF, 0xF))
    seen = set(start)
    queue = deque(start)
    deadly = []
    parent = {s: None for s in start}
    while queue:
        st = queue.popleft()
        letters2, jm, rm = st
        for letter in letters:
            nl, nj, nr = step(letters2, jm, rm, letter)
            ns = (nl, nj, nr)
            if ns not in seen:
                seen.add(ns)
                parent[ns] = (st, letter)
                queue.append(ns)
                if nr != 0 and nj == 0:
                    deadly.append(ns)
    print(f"reachable DFA states: {len(seen)}; level-2 deadly states: {len(deadly)}")
    for ns in deadly[:5]:
        # reconstruct word
        word = []
        cur = ns
        while parent[cur] is not None:
            cur, letter = parent[cur]
            word.append(letter)
        first = cur[0]
        word = [first[0], first[1]] + word[::-1]
        print("  deadly word d0=", "".join(str(a) for a, _ in word),
              "d1=", "".join(str(b) for _, b in word))
    if not deadly:
        print("NO level-2 deadly straight segment exists at ANY length.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
