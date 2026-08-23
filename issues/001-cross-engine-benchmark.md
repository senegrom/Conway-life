# Cross-engine Game of Life benchmark

## Question

Where are the practical crossover boundaries among HashLife, StreamLife, sparse-tile and dense-GPU engines?

## Engines

Golly 5.0, lifelib, `gol_engines`, Binary Banter, CAT and apgsearch.

## First deliverable

A small suite with three correctness patterns, one dense torus, one sparse expanding pattern, one long HashLife pattern and one stream-dominated pattern, with raw JSON, final-state hashes and exact commits.

## Acceptance criteria

- independent output verification;
- at least three repetitions per engine/workload;
- peak memory;
- initialization separated;
- no cross-family geometric mean;
- reproduction notes for every public performance claim.

## Publication route

Repository release first; JOSS when feature-complete; CA/HPC paper only if new algorithmic conclusions emerge.
