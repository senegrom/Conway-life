# A Garden of Eden its live cells do not reveal

*The explicit f = 1 witnesses for the Salo–Törmä padding constant
(open question [Q28820954], LIFE-F001 in this repository). Found
2026-08-26/27 by exhaustive census; every claim below re-verified fresh
on 2026-08-28.*

[Q28820954]: https://arxiv.org/abs/1912.00692

## The pattern

11×11, 69 live cells, fully symmetric under the square's symmetry group D4:

```
0 1 0 1 0 1 0 1 0 1 0
1 1 1 0 1 1 1 0 1 1 1
0 1 0 0 1 1 1 0 0 1 0
1 0 0 1 0 1 0 1 0 0 1
0 1 1 0 1 0 1 0 1 1 0
1 1 1 1 0 1 0 1 1 1 1
0 1 1 0 1 0 1 0 1 1 0
1 0 0 1 0 1 0 1 0 0 1
0 1 0 0 1 1 1 0 0 1 0
1 1 1 0 1 1 1 0 1 1 1
0 1 0 1 0 1 0 1 0 1 0
```

```
x = 11, y = 11, rule = B3/S23
bobobobobo$3ob3ob3o$bo2b3o2bo$o2bobobo2bo$b2obobob2o$4obob4o$b2obobob2
o$o2bobobo2bo$bo2b3o2bo$3ob3ob3o$bobobobobo!
```

Call it **W**. Two machine-verified facts about W:

**Fact 1 — the 11×11 window is *not* an orphan.** There is a 13×13
preimage patch whose one-generation B3/S23 image agrees with W on all
121 window cells. Here is one, found by SAT and independently re-stepped
(the outer ring is the +1 margin; its own image outside the window is
irrelevant and unconstrained):

```
1 0 0 1 1 0 0 1 0 1 0 0 1
0 0 1 0 0 0 1 0 1 0 1 0 0
0 1 1 0 1 0 1 1 0 0 1 1 0
1 0 0 0 0 0 0 0 0 0 0 0 1
1 1 0 0 0 1 0 0 1 0 0 1 1
0 0 0 1 0 1 0 1 0 1 0 0 0
1 0 1 0 1 0 0 1 0 0 1 0 1
0 1 0 0 0 0 0 0 0 0 1 0 0
1 1 0 0 1 0 1 0 1 0 0 1 0
0 0 1 1 1 1 0 1 1 1 1 0 1
1 0 0 1 0 0 0 0 0 1 0 0 1
1 0 0 0 0 0 1 0 0 0 0 0 0
1 1 0 1 0 1 0 1 0 1 0 1 0
```

**Fact 2 — one ring of dead cells makes it an orphan.** The 13×13
window consisting of W surrounded by a ring of cells specified *dead*
has **no** 15×15 preimage patch at all (SAT: UNSAT). No configuration of
the infinite plane containing that 13×13 arrangement has a predecessor.

## What the two facts mean together

A configuration is a Garden of Eden — has no predecessor — **iff** some
finite window of it is an orphan (one direction is immediate; the other
is König's lemma on partial preimages). So GoE-ness always has a finite
certificate. The question is what the certificate must contain.

- By Fact 2, **W placed on an otherwise dead plane is a Garden of
  Eden**: that configuration contains the dead-ringed window.
- By Fact 1, **no certificate lives inside the bounding box**. The
  11×11 window is preimageable, and so is every sub-window of it.
  Worse: extending the patch above arbitrarily to a full configuration
  and stepping it shows that W *does* occur one step into the future —
  in the right (live) context, W is perfectly reachable.

The obstruction is therefore carried by the **dead cells**: W-with-dead-
surroundings is unreachable, W-with-the-right-live-surroundings is
reachable, and you cannot tell which case you are in from the live cells
alone. Stare at the bounding box as long as you like — the Garden of
Eden is invisible until the certificate window includes one ring of the
silence around the pattern.

## The open question this feeds

Salo–Törmä (arXiv:1912.00692, Theorems 3/5) prove: if the
finite-support configuration of a pattern P is a GoE, then pad⁴(P) — P
with **four** rings of specified-dead padding — is already an orphan.
Since a preimage patch of a thicker padding restricts to one of a
thinner padding, preimage existence is anti-monotone in the ring count,
and each P has a well-defined **flip point** f(P) = least c with
pad^c(P) an orphan, with f(P) ∈ {0, 1, 2, 3, 4, ∞} and f(P) < ∞ exactly
when P-on-a-dead-plane is a GoE.

**Open: the optimal padding constant c\* = max finite f(P).** The
theorems give c\* ≤ 4; the paper notes c\* ≥ 1 without exhibiting a
pattern. W has f(W) = 1 exactly, so it **witnesses c\* ≥ 1 explicitly**
— to our knowledge the first such exhibit (prior-art caveat below).

Why did this need a search at all? Every published Garden of Eden we
could obtain (nine, from Banks 1971 through the current 45-cell and
five-row records) has f = 0: the bare bounding box is *already* an
orphan (`scripts/verify_goe_zoo.py`). The known-GoE literature optimises
for small certificates, so it systematically produces f = 0 patterns; f
≥ 1 witnesses had to be found by exhaustive enumeration — they are rare
even where they live (4 of the 346 D4-symmetric 11×11 dead-ringed
orphans, ~1%).

What remains of the question is the gap between 1 and 4: does any
pattern have f ≥ 2 — a GoE needing *two* rings of dead context in its
certificate? Complete searches so far say no rotationally symmetric core
up to 11×11 does (D4/C4 9×9, D4 11×11, all exhaustive and empty); the
hunt continues at 13×13 and in asymmetric flip neighbourhoods.

## The full family

Four fully D4-symmetric witnesses, from the complete 11×11 census
(`d4-ring-orphans-11x11.txt`, headers `F1-WITNESS`):

| population | orbit-code | note |
|---|---|---|
| 84 | 946939 | |
| 73 | 1457786 | |
| 69 | 1500906 | **W above** |
| 69 | 1807033 | second minimal-population witness |

plus 60 near-D4 single-flip variants (populations 68–85) from the
census's complete flip-neighbourhood sweep — 64 verified witnesses in
all (see `docs/research-log.md`, 2026-08-26/27 entries).

## Verify it yourself

Only `scripts/preimage_sat.py` is needed (pysat; the encoding is
exhaustively cross-checked against brute force at small sizes and
against nine independent published orphans on the UNSAT side). Put W in
`w.txt` as eleven rows of 0/1 as printed above, and W with a dead ring
in `w_ring.txt` (thirteen rows: a row of thirteen 0s, then each W row
with a 0 on both ends, then a row of thirteen 0s):

```
$ python scripts/preimage_sat.py check w.txt        # SAT + verified patch
$ python scripts/preimage_sat.py check w_ring.txt   # UNSAT: ORPHAN
```

The first command prints a (possibly different) preimage patch and
re-steps it before claiming SAT; the second's UNSAT is the orphan claim.
`scripts/padding_flip.py` wraps the same checks as a flip-point
computation.

## Provenance and caveats

- Found by `scripts/ring_orphan_search.py` (incremental-SAT census of
  all 2,097,151 D4-symmetric 11×11 cores); every find re-verified with
  the independent slow checker, 0 mismatches; the four witnesses and the
  patch above re-verified again fresh for this document.
- "First explicit witness" is pending a prior-art audit on the
  ConwayLife forums (not reachable from our tooling); the fallback claim
  is independent discovery. The mathematical content — f(W) = 1, hence
  c\* ≥ 1 by exhibit — is machine-checked and unconditional.
- Related but distinct: the same census contains a 45-cell fully
  D4-symmetric orphan tying the smallest-known-orphan population — see
  `README.md` in this directory.
