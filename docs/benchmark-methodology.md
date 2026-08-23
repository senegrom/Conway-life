# Benchmark methodology

## Objective

Measure algorithmic crossover regions, not merely crown a winner.

The benchmark must answer:

- Which engine is fastest for this **workload class**?
- At what size/generation/density does the ranking change?
- What memory is required?
- Is the result exact and reproducible?
- How much performance comes from warm memoization?
- Does the engine fail gracefully when memory is exhausted?

## Workload families

### A. Sanity and correctness

- block, blinker, glider;
- R-pentomino at pinned checkpoints;
- small toroidal random grids cross-checked against `scripts/reference_life.py`.

### B. Long/compressible

- HashLife-friendly oscillators and spaceships;
- recursively metafied patterns;
- 0E0P metaglider;
- generation targets \(2^8,2^{12},2^{16},\ldots\) as feasible.

### C. Dense/chaotic

For each size and density, generate a pinned bit grid from a cryptographic seed:

- 4096², 16384² and largest feasible;
- densities 0.1, 0.3, 0.5;
- toroidal topology;
- 1,000; 10,000; and 100,000 explicit generations where feasible.

Avoid timing file parsing as update time. Record initialization separately.

### D. Sparse expanding

- guns;
- puffers;
- breeders;
- methuselahs;
- patterns whose bounding boxes grow while density falls.

### E. Stream-dominated

- Demonoid/Orthogonoid-style patterns;
- 0E0P;
- synthetic antiparallel glider tapes with controlled lane spacing.

### F. Soup census

- fixed symmetry;
- fixed rule;
- fixed client version;
- fixed number of soups;
- end-to-end throughput including CPU classification and upload-disabled result packaging.

## Required run record

Every JSON result must include:

- schema version;
- engine and algorithm IDs;
- exact source version/commit;
- workload ID and input SHA-256;
- topology, dimensions and generations;
- command;
- start timestamp;
- wall time and initialization/update split where available;
- peak RSS and peak VRAM where available;
- exit status;
- output SHA-256 or canonical state digest;
- CPU, GPU, RAM, operating system, compiler and flags;
- notes and failure mode.

## Timing policy

1. Run one untimed correctness pass.
2. Record at least five timed repetitions for short jobs; at least three for longer jobs.
3. Randomize engine order.
4. Report median, minimum, maximum and median absolute deviation.
5. Record cold process start and warm in-process performance separately.
6. Synchronize the GPU before stopping the clock.
7. Exclude rendering.
8. Include host/device transfers in an end-to-end column and exclude them only in a clearly labelled kernel-only column.
9. Lock or record GPU power limit and clock policy.
10. Record thermal throttling indicators where possible.

## Correctness policy

- Small bounded cases: compare every cell to the reference implementation.
- Large bounded cases: compare a cryptographic hash of the exact bit grid.
- Sparse infinite cases: compare sorted live-cell coordinates when feasible.
- HashLife huge-time cases: compare independent engines at smaller checkpoints, population, bounding box and selected hashed subregions at the target.
- Search results: replay in two independent simulators.
- UNSAT results: retain solver proof logs where supported and replay with an independent checker.

## Statistical reporting

Do not overfit to one pattern. Report:

- per-workload values;
- geometric mean only within a coherent workload family;
- Pareto front of time versus memory;
- crossover plots against density, size and generation depth;
- failure region;
- confidence/dispersion across runs.

## Things not to do

- Do not compare HashLife's skipped generations to dense CUPS.
- Do not report only the best run.
- Do not omit initialization when it is material.
- Do not change topology silently.
- Do not compare Golly GUI rendering against a headless kernel.
- Do not use an unpinned “latest” dependency.
- Do not accept an engine's self-reported output without a digest.

## Proposed benchmark paper questions

1. Can simple structural metrics predict the winning representation?
2. What is the practical parallel scaling of HashLife and StreamLife?
3. Where does GPU temporal blocking beat CPU bit-parallel evolution?
4. How does memory pressure alter HashLife's advantage?
5. Can a hybrid dispatcher achieve within 20% of the best specialist across all classes?
