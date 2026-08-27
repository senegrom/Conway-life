# First-party discoveries

## d4-ring-orphans-11x11.txt

The complete census of fully D4-symmetric 11×11 patterns whose
thickness-1 dead-ring padding (13×13 window) is an **orphan** — found
2026-08-26/28 by exhaustive enumeration of all 2,097,151 orbit-subset
candidates with `scripts/ring_orphan_search.py` (incremental-SAT
templates), every find re-verified with the independently and
exhaustively validated `scripts/preimage_sat.py`.

**Census: 346 patterns, populations 45–85.** Each entry is headed by its
classification:

- `DEAD-RINGED-ORPHAN` (342): the bare 11×11 core is itself an orphan.
  The population-45 member ties the smallest-known-orphan cell count
  while carrying the maximal square symmetry group — and it is NOT the
  known (asymmetric) 45-cell orphan.
- `F1-WITNESS` (4, populations 84/73/69/69): the bare core HAS a preimage
  patch, but the dead-ringed window does not — the first explicit
  witnesses that the Salo–Törmä padding constant (open question
  Q28820954, LIFE-F001) is at least 1. For these patterns
  f(P) = 1: the finite-support configuration is a Garden of Eden whose
  bounding-box pattern alone does not reveal it.

Verification: every raster's bare and ringed windows re-checked by
`preimage_sat.check_window` (346/346 verified, 0 mismatches). Any claim
can be replayed from the raster alone. Status caveats: "smallest known
orphan" and novelty of the witness class are pending a ConwayLife-forum
prior-art audit (site inaccessible to our tooling; see the research log
and docs/drafts/forum-post-four-row-goe.md).
