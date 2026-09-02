# First-party discoveries

Machine-verified artefacts produced by this repository. Every claim here can be
replayed from the raster or JSON alone with `scripts/preimage_sat.py`; the
searches that produced them are in `scripts/` and `modal/`, and the narrative is
in `docs/research-log.md`.

## f1-witness.md

Standalone explainer for the **f = 1 padding witnesses**: an 11×11 pattern that
is a Garden of Eden on an empty plane, yet whose bounding-box window has a
preimage — so no certificate of its Garden-of-Eden-ness fits inside its own
bounding box. Contains the witness, an explicit verified 13×13 preimage patch,
the definitions, why this pins the Salo–Törmä padding constant at ≥ 1, and a
two-command re-verification recipe.

## d4-ring-orphans-11x11.txt

The complete census of fully D4-symmetric 11×11 patterns whose thickness-1 dead
ring padding is an orphan — all 2,097,151 orbit-subset candidates, every find
re-verified by the independently validated checker (346/346, 0 mismatches).

- `DEAD-RINGED-ORPHAN` (342): the bare core is itself an orphan. The
  population-45 member ties the smallest-known-orphan cell count while carrying
  the maximal square symmetry group, and is **not** the known (asymmetric)
  45-cell orphan.
- `F1-WITNESS` (4, populations 84/73/69/69): the bare core has a preimage but
  the dead-ringed window does not — the first explicit witnesses for the padding
  constant being ≥ 1.

## witnesses15-two-ring.json

**5,692 fifteen-by-fifteen f = 1 witnesses** (bare window preimageable,
thickness-1 padding an orphan), mined on Modal from all 37,355,520 two-ring D4
extensions of the known 11×11 witnesses. These are the first witnesses whose
side length reaches the threshold at which a level-2 padding obstruction is
structurally possible (see `deadly-boundary-words.txt`). Stored as
`(source label, ring code)` pairs plus the family totals; rasters are
reconstructed by `modal/f2_ring_extend_modal.py`.

## deadly-boundary-words.txt

All **minimal level-2 deadly boundary words** of lengths 14–17 (32 / 202 /
1,052 / 4,967), from the subset-construction automaton in
`scripts/boundary_deadly_dfa.py`. A boundary word is level-2 deadly when the
first padding ring can be killed but the first two cannot be killed together —
the *only* mechanism by which a pattern can have padding flip point 2. Their
minimum length of 14 is why every f = 2 search below that size was structurally
doomed. Verified independently by transfer-matrix DP and by direct SAT.

## c4-11x11-small-orphan-census.json

Complete census of every C4-symmetric 11×11 pattern with population ≤ 45, i.e.
every candidate that could tie or beat the smallest-known-orphan record
(215,272,804 candidates, run on Modal). Exactly **one** orphan exists in that
space: the known 45-cell pattern. Hence **no C4-symmetric 11×11 Garden of Eden
has ≤ 44 cells**, and the 45-cell one is unique among C4-symmetric 11×11
Gardens of Eden with ≤ 45 cells.

## Status caveats

"Smallest known orphan", "first explicit witness" and similar novelty claims are
pending a ConwayLife-forum prior-art audit (the site is not reachable from this
project's tooling); the fallback claim is independent discovery. The
mathematical content — each verified orphan, witness and census — is
machine-checked and unconditional.
