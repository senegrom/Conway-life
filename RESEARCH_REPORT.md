# Research report: Conway's Game of Life

**Prepared:** 2026-08-23  
**Scope:** Conway's Life, B3/S23, with emphasis on very large and very long simulations, open problems, search infrastructure and publication routes.

## Executive assessment

The phrase “fastest simulator” hides at least five different computational tasks. A simulator that is extraordinary on one can be unusable on another.

| Task | Best current starting point | Why |
|---|---|---|
| Evolve a regular, sparse or recursively constructed pattern for an enormous number of generations | Golly HashLife, lifelib HashLife; benchmark `gol_engines` parallel HashLife | Memoized quadtrees reuse repeated space-time computations and can jump many generations |
| Evolve self-replicators and engineered patterns dominated by separated antiparallel glider or xWSS streams | lifelib StreamLife; benchmark `gol_engines` parallel StreamLife | Separates non-interacting streams before recursive evolution |
| Evolve a huge bounded, dense or chaotic grid for every generation | Binary Banter CUDA/OpenCL; CAT `PACK`; strong SIMD CPU baselines | Bit packing and temporal blocking maximise explicit cell updates |
| Run millions or billions of random soups and classify ash | apgsearch/apgluxe backed by lifelib tile algorithms and optional CUDA screening | Designed for Monte Carlo soup throughput and Catagolue submission |
| Find a spaceship, oscillator, conduit, synthesis or predecessor satisfying constraints | LSSS/LLSSS, ikpx2, CatForce/Bellman, Logic Life Search, custom SAT/SMT | Search structure matters more than raw forward-simulation throughput |

The practical recommendation is therefore a **portfolio**, not a winner:

1. install Golly 5.0 as the interactive and correctness baseline;
2. install lifelib for programmable HashLife, StreamLife and tile-based work;
3. reproduce the `gol_engines` parallel HashLife/StreamLife claims;
4. use the RTX GPU for dense CUDA benchmarks and apgsearch;
5. use specialised search tools or SAT/SMT for open questions.

### What appears genuinely missing

I did not find a maintained, standard, cross-engine leaderboard with a pinned pattern corpus, exact commits, common hardware, common boundary conditions and correctness digests. Existing numbers are useful but not directly comparable. Creating that benchmark is itself a worthwhile research-software contribution.

## 1. Why “very long” and “very big” are different

### Very long

The target generation may be \(10^{12}\), \(2^{100}\), or much larger, but the pattern may contain extreme repetition. HashLife can cache the evolution of identical quadtree nodes and reuse it. Runtime is then not proportional to “number of cells × number of generations.” Reporting cell-updates per second is usually meaningless.

HashLife's weakness is high entropy. Golly's own documentation says it performs very poorly on highly chaotic patterns and recommends QuickLife there.[S1]

### Very big

The grid may contain billions of explicitly represented cells and remain chaotic. Every generation has to be processed, so the problem becomes memory bandwidth, bitwise throughput, halo exchange, temporal blocking and possibly out-of-core execution. Dense GPU engines are appropriate, but they do not provide HashLife's generation skipping.

### Big and long

A high-entropy grid that is both enormous and must be advanced through many explicit generations is the hardest regime. There is no known general shortcut: the engineering questions are compression, partitioning, multi-step tiling, multiple GPUs, host/device streaming, checkpointing and fault recovery.

## 2. Simulator landscape

### 2.1 Golly 5.0

Golly is the mature, cross-platform reference environment. Version 5.0 was released on 26 October 2025, and the project was still receiving updates in August 2026.[S2][S3] Its relevant engines are:

- **HashLife:** excellent for patterns with repeated structure in space or time;
- **QuickLife:** a fast conventional non-hashing algorithm for chaotic or unsuitable patterns.

Use Golly first to inspect patterns, convert formats and establish small correctness checks. It is not necessarily the fastest headless engine on every workload.

### 2.2 lifelib

Adam P. Goucher's lifelib is a high-performance C++ library with generated low-level iterators and multiple containers.[S4][S5]

- **HashLife / `pattern`:** default for repeated structure.
- **StreamLife / `streamtree`:** specialised for separated antiparallel glider and standard-spaceship streams; can be orders of magnitude faster on suitable engineered patterns but is usually slower elsewhere.
- **Tile-based / `upattern`:** uncompressed overlapping tiles; tracks tiles needing updates and is suited to random soups.

This is the most important programmable toolkit because it covers multiple workload classes and underlies apgsearch and other community software.

### 2.3 `gol_engines`: parallel HashLife and StreamLife

The Rust project `das67333/gol_engines` implements synchronous and asynchronous HashLife and StreamLife, fixed-size open-addressing hash tables, memory caps, macrocell I/O and parallel recursive execution.[S6]

Its author reports the following on one 0E0P metaglider workload, using a 32-logical-core, 96-GiB cloud machine:

- \(2^{14}\) generations with HashLife: 41.7 s update for the asynchronous engine versus 848.5 s for Golly 4.3 and 912.1 s for lifelib.
- \(2^{27}\) generations with StreamLife: 186.9 s for asynchronous StreamLife versus 991.1 s for lifelib.

These are striking **self-benchmark** results, not yet a universal ranking. The benchmark uses one unusually parallel, HashLife-friendly pattern and older Golly 4.3. Independent reproduction should be an early repository task.

### 2.4 Dense CUDA/OpenCL: Binary Banter

`binary-banter/fast-game-of-life` is a compact Rust/CUDA/OpenCL implementation aimed at dense Life.[S7][S8] It combines bit-packed cells, SIMD and CPU multithreading, temporal blocking, shared-memory tuning, CUDA `LOP3` logic and warp shuffles.

The authors report 11.720 trillion cell updates per second on an NVIDIA A40, 9.871 trillion on a V100, and 9.666 trillion on a 2080 Ti. The CPU multithreaded result on an i9-11900K was 296.019 billion cell updates per second.[S8]

These numbers are useful engineering evidence but are from a 2023 author benchmark. The code does not solve sparse infinite-universe or HashLife workloads, and the authors note that universes larger than GPU memory were not handled.

### 2.5 CAT: packet coding versus tensor cores

The peer-reviewed CAT work evaluates explicit GPU cellular-automaton algorithms on modern NVIDIA hardware.[S9] For standard radius-1 Life, its packet-coded CUDA method (`PACK`) is the relevant contender; CAT's tensor-core method is competitive but is surpassed at low radius. From radius 3 upward in Larger-than-Life rules, tensor cores increasingly dominate, reaching up to roughly 14× over the fastest competing approach in the reported experiments.

For Conway Life specifically, CAT is valuable because `PACK` is a modern explicit-grid baseline and the paper supplies a careful method taxonomy. It does **not** displace HashLife for compressible, very-long-time evolution.

### 2.6 apgsearch

apgsearch generates random soups, stabilises them, classifies the products and submits results to Catagolue, where hauls are peer reviewed.[S10] Version 5.x supports CUDA screening. This is the correct tool for distributed object census questions, not for arbitrary single-pattern simulation.

### 2.7 CAX and adjacent libraries

CAX is a JAX-based, hardware-accelerated cellular-automata library supporting discrete, continuous and neural automata.[S11] It is attractive for batched experiments, differentiable work and broad CA research. It should not be described as the fastest pure-Life engine without a workload-specific comparison.

## 3. A defensible “fastest” answer

| Workload | First engine to try | Comparator | Main caveat |
|---|---|---|---|
| Regular pattern, astronomical generation | Golly HashLife or lifelib HashLife | `gol_engines` async HashLife | Performance depends on repeated substructure and memory |
| 0E0P/Demonoid/Orthogonoid-like streams | lifelib StreamLife | `gol_engines` async StreamLife | Specialised; may lose on ordinary patterns |
| Chaotic bounded Life | Binary Banter CUDA, CAT `PACK` | Golly QuickLife and SIMD CPU | Fixed-grid/boundary choices must match |
| Random 16×16 soups | apgsearch CUDA/CPU | lifelib tile-based custom harness | Metric should be soups/s and verified objects, not CUPS |
| General exploratory use | Golly 5.0 | lifelib Python/C++ | Convenience rather than universal peak speed |

The only scientifically sound way to improve this table is to run a common suite.

## 4. Open questions

### 4.1 Formal questions on an author-maintained list

Ville Salo maintains a dated open-problem page. Its Life section currently lists:[S12]

1. **Optimal padding thickness.** Determine the smallest zero-padding thickness that guarantees all thicker paddings occur in an image whenever that padding does.
2. **Finite-support predecessor decidability.** Decide whether a given finite-support configuration has a finite-support predecessor.
3. **Smallest periodic counterexample.** Find the minimum period/fundamental domain of a periodic configuration with a predecessor but no spatially periodic predecessor.
4. **Generic nilpotence.** Is Life generically nilpotent?
5. **Sensitivity.** Is Life sensitive to initial conditions?
6. **Temporal-periodic density.** For each temporal period \(p\), are finite-support points dense in the \(p\)-periodic subshift?
7. **Strong irreducibility.** For each \(p\), is the \(p\)-periodic subshift strongly irreducible?

These have the best status provenance in this survey because the page is maintained by an active author in the area. Open status should still be rechecked before a major run.

### 4.2 Questions from the 2025 preimage paper

Salo and Törmä's 2025 paper proves that finite-support predecessor existence is NP-complete, orphans are coNP-complete, periodic-predecessor existence is undecidable, and gives a \(6210\times37800\)-periodic configuration with predecessors but no periodic predecessors.[S13]

It leaves major directions:

- **Still-life finitization:** are finite-support fixed points dense among all fixed points?
- **Strong block-map universality:** Life is proved semiweakly universal; is it strongly universal?
- **Higher powers:** can comparable backward-computation results be proved for multiple Life steps?
- **Universal backward chains:** are there configurations for which every predecessor chain performs universal computation backwards?

Strong block universality was independently reviewed as still open in July 2026, with some bounded periodic-fibre exclusions recorded, but TheoremDB is a secondary tracker rather than the canonical source.[S14]

### 4.3 Concrete community questions

These are easier to state and often more computationally approachable, but their status is dynamic.

#### Four-row Garden of Eden

It is known that no height-4 orphan exists under the usual specified-cell definition, but LifeWiki still records as open whether a Garden of Eden can have its **live cells** restricted to four consecutive rows.[S15]

This is an excellent SAT/transfer-matrix target: exact statement, finite-width structure, straightforward independent verification of any candidate.

#### Spaceship gaps

The LifeWiki Spaceship Search Status Page records proved minima, completed censuses and remaining search gaps.[S16] The current ikpx2 tutorial gives examples of unknown speeds including \((2,1)c/7\), \(c/8\), \(3c/8\) and diagonal \(c/9\).[S17] These examples must be checked immediately before launching because discoveries can happen between wiki edits.

#### Unsynthesizable still lifes

The smallest known still life proved impossible to synthesise with gliders was reduced from 306 cells in 2022 to 154 cells by April 2025. The current threshold is therefore known only to satisfy \(22 < p \le 154\), where \(p\) is the first population at which not every still life is constructible.[S18] Reducing 154 or raising the lower bound are concrete targets.

#### Glider destruction and invulnerability

LifeWiki lists unresolved questions about two-glider destruction, glider-proof targets, targets resistant to unidirectional slow salvos and fully invulnerable finite targets. The page labels its list “as of September 2023,” so every item is **needs-recheck**, not a current-status guarantee.[S19]

## 5. Solved problems that stale lists may still call open

Do not start expensive work before checking recent papers.

- The generalized grandfather problem and one interpretation of the unique-father problem were solved in 2022.[S20]
- The existence and complexity of several predecessor/orphan problems were settled in the 2025 preimage paper.[S13]
- Omniperiodicity of Life has been solved; it should not be copied from old challenge lists as open.
- Community pattern records change continuously; LifeWiki reported new large and oblique spaceships in 2025–2026.

## 6. Where problems and results are collected

### Formal theory

- Ville Salo's open-problem page: compact, precise and author maintained.
- Primary papers, especially their concluding questions.
- TheoremDB: useful as a dated secondary status/audit layer, never a substitute for primary sources.

### Community construction and search

- **LifeWiki:** encyclopaedia, status pages, program tutorials and pattern files.[S21]
- **ConwayLife forums:** the active discussion and first-report venue; forum guidance asks users to post discoveries before creating wiki pages.[S22]
- **Catagolue:** distributed census database fed by apgsearch, with haul verification.
- **Spaceship Search Status Page:** widths, heights, complete censuses and proof links.
- **Program-specific forum threads:** practical search parameters, partials and negative runs.

### Minimum discovery packet

Every claimed improvement should include:

1. exact RLE/macrocell or formal instance;
2. rule, topology and coordinate convention;
3. program name, version and commit;
4. complete command line and environment;
5. search bounds and stopping condition;
6. logs/checkpoints;
7. independent verifier;
8. SHA-256 hashes of artefacts;
9. license and authorship;
10. a plain-language comparison with the prior record.

## 7. Where to publish improvements

| Contribution | First publication route | Formal route |
|---|---|---|
| New pattern or record | ConwayLife forum, independent verification, Catagolue where applicable, then LifeWiki | Complex Systems or Journal of Cellular Automata if there is broader method/science |
| Faster implementation or benchmark suite | public repository, upstream issue/merge request, reproducibility report | Journal of Open Source Software when feature-complete; JCA, Complex Systems or an HPC venue for algorithmic novelty |
| Search algorithm | repository + forum demonstration + benchmark corpus | AUTOMATA/ACRI, JCA, Complex Systems; systems/HPC venue if generally applicable |
| Theorem or complexity result | arXiv preprint plus code/certificates | Theoretical Computer Science, AUTOMATA, JCA or a suitable theory venue |
| Reproduction of old performance claim | public benchmark and archived environment | ReScience C or a research-software/reproducibility venue |

The Journal of Cellular Automata explicitly accepts theoretical CA work and CA computational models, including full papers and short communications.[S23] Complex Systems accepts accessible work on systems with simple components and complex behaviour, has web/email submission and no publication charges.[S24] JOSS requires meaningful, feature-complete, maintainable, OSI-licensed research software with documentation and tests.[S25] AUTOMATA is the recurring specialist conference series for cellular automata and discrete complex systems.[S26]

## 8. Prioritised research portfolio

Scores are judgement calls, not factual rankings.

| Project | Novelty | Tractability | Fit to current hardware | Verification clarity | Recommendation |
|---|---:|---:|---:|---:|---|
| Cross-engine benchmark suite | 3/5 | 5/5 | 5/5 | 5/5 | Start immediately |
| Four-row Garden of Eden | 5/5 | 3/5 | 4/5 | 5/5 | Primary open-question attack |
| Exact padding constant | 5/5 | 2/5 | 4/5 | 5/5 | Second SAT line |
| Reduce periodic no-periodic-preimage example | 5/5 | 2/5 | 4/5 | 4/5 | Ambitious optimisation target |
| Spaceship gap with LSSS/LLSSS/ikpx2 | 4/5 | 3/5 | 5/5 | 4/5 | Good community result route |
| Smaller unsynthesizable still life | 4/5 | 3/5 | 4/5 | 5/5 | Strong hybrid search/theory route |
| Strong block universality | 5/5 | 1/5 | 2/5 | 5/5 | Long-horizon theory programme |

## 9. Benchmark design

### Workload families

1. **Long/compressible:** metapixels, breeders, 0E0P-like constructions; targets \(2^k\) generations.
2. **Dense/chaotic:** fixed toroidal grids at several sizes and densities with pinned random seeds.
3. **Sparse expanding:** methuselahs, guns, puffers and breeders.
4. **Stream-dominated:** Demonoid/Orthogonoid/0E0P-style glider streams.
5. **Soup census:** batches of 16×16 soups under fixed symmetries.
6. **Memory stress:** patterns selected to fill hash tables or VRAM and exercise garbage collection.

### Required measurements

- wall-clock initialization and update time separately;
- peak host memory and peak VRAM;
- exact output digest/checkpoint;
- source commit, compiler, flags, driver and hardware;
- topology and boundary;
- population/dimensions where meaningful;
- cold and warm runs;
- repeated trials with median and dispersion;
- failure mode, including out-of-memory and hash-table restart.

### Comparison rules

- Never compare HashLife and dense-grid CUPS as though they perform the same operations.
- Include initialization and exclude it in separate columns rather than hiding it.
- Pin all input bytes and verify their SHA-256.
- Use identical topology and generation count.
- Report the result of a simple trusted reference implementation on small instances.
- Publish negative results and crossover points, not just winning cases.

## 10. Concrete setup for the available Windows/RTX machine

- Use **native Golly 5.0** for exploration and visual checks.
- Use **WSL2 Ubuntu** for lifelib, `gol_engines`, LSSS, LLSSS and ikpx2.
- Use **CUDA under WSL2 or native Windows**, depending on the project build, for Binary Banter, CAT and apgsearch.
- Keep benchmark data on a fast local SSD, not a network-mounted directory.
- Record GPU model, driver, power limit and clock policy; dense kernels are sensitive to all of them.
- Do not assume GPU superiority for HashLife or SAT search. CPU memory capacity and single-thread latency may be decisive.

## 11. Potential simulator-improvement papers

The benchmark may reveal publishable systems questions:

1. **Adaptive hybrid evolution:** choose HashLife, sparse tile or dense GPU per region using measured entropy, repetition and active-frontier density.
2. **Parallel HashLife reproducibility:** deterministic memo-table partitioning and scalable garbage collection.
3. **GPU leaf kernels for a quadtree engine:** accelerate base cases while preserving HashLife's recursive jumps.
4. **Out-of-core temporal blocking:** evolve grids larger than VRAM with overlap-minimising halo schedules.
5. **Multi-GPU Life:** quantify communication/computation crossovers under multi-step tiling.
6. **Portable bitwise synthesis:** automatically generate minimum-instruction Boolean kernels for CUDA `LOP3`, AVX-512 and future ISAs.
7. **Certificate-first search:** make SAT proofs, UNSAT cores and replay validators first-class outputs for Life searches.

## 12. Recommended next decision

Adopt this repository as the evidence ledger and make the first milestone a small, reproducible benchmark release. In parallel, formalise the four-row Garden-of-Eden statement and build a certificate-checking SAT prototype. The benchmark gives an early publishable asset; the Garden-of-Eden line offers a direct route to a genuine open result.

## Sources

[S1]: https://golly.sourceforge.io/Help/Algorithms/HashLife.html  
[S2]: https://sourceforge.net/projects/golly/files/golly/golly-5.0/  
[S3]: https://sourceforge.net/projects/golly/  
[S4]: https://gitlab.com/apgoucher/lifelib  
[S5]: https://conwaylife.com/wiki/Lifelib  
[S6]: https://github.com/das67333/gol_engines  
[S7]: https://github.com/binary-banter/fast-game-of-life  
[S8]: https://binary-banter.github.io/game-of-life/  
[S9]: https://arxiv.org/abs/2406.17284  
[S10]: https://conwaylife.com/wiki/Apgsearch  
[S11]: https://arxiv.org/abs/2410.02651  
[S12]: https://villesalo.com/openproblems.html  
[S13]: https://doi.org/10.1016/j.tcs.2025.115237  
[S14]: https://www.theoremdb.org/statements/P2830/  
[S15]: https://conwaylife.com/wiki/Garden_of_Eden  
[S16]: https://conwaylife.com/wiki/LifeWiki:Spaceship_Search_Status_Page  
[S17]: https://conwaylife.com/wiki/Tutorials/ikpx2  
[S18]: https://conwaylife.com/wiki/Glider_synthesis  
[S19]: https://conwaylife.com/wiki/Glider_destruction  
[S20]: https://doi.org/10.4230/LIPIcs.ICALP.2022.131  
[S21]: https://conwaylife.com/wiki/  
[S22]: https://conwaylife.com/forums/  
[S23]: https://www.oldcitypublishing.com/journals/jca-home/  
[S24]: https://www.complex-systems.com/  
[S25]: https://joss.theoj.org/about  
[S26]: https://www.automataandacri2026.ugent.be/
