# Four-row live-cell Garden of Eden

## Problem

Determine whether a Garden of Eden exists whose live cells lie within four consecutive rows.

## Important distinction

This is not the same as a four-row orphan. The latter has a stronger specified-live-and-dead-cell formulation.

## Plan

1. Write the exact strip and predecessor semantics.
2. Reproduce known height-5 examples and the height-4 orphan result where artefacts are available.
3. Encode one-step predecessors using a column transfer relation and SAT.
4. Search increasing widths with symmetry breaking.
5. For SAT, emit exact RLE and independently verify absence of a predecessor.
6. For UNSAT, retain DRAT/LRAT proof logs where supported and replay them.
7. Analyse repeated boundary states to seek an unbounded-width proof.

## Completion criteria

A verified candidate, or a theorem/certificate excluding all widths.

## Source

https://conwaylife.com/wiki/Garden_of_Eden
