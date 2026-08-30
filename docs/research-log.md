# Research log

## 2026-08-23 — initial landscape review

### Findings

- No universal fastest simulator exists; workload classification is mandatory.
- Golly 5.0 is the mature reference and is actively maintained.
- lifelib spans HashLife, StreamLife and tile-based workloads.
- `gol_engines` is a promising parallel HashLife/StreamLife contender with strong author-reported results that need independent reproduction.
- Binary Banter and CAT `PACK` are strong dense-grid baselines.
- CAT tensor cores are more relevant to Larger-than-Life radii than to standard radius-1 Conway Life.
- apgsearch/Catagolue is the production route for random soup census.
- Formal open problems are best sourced from Ville Salo's maintained page and the 2025 preimage paper.
- Old challenge lists are dangerous: several predecessor and period questions were solved in 2022–2025.
- No maintained standard cross-engine benchmark was found.

### Decisions

- Treat the benchmark as the first repository deliverable.
- Treat the four-row Garden-of-Eden question as the first direct open-question target.
- Use evidence labels and last-checked dates.
- Require independent checkers for both patterns and UNSAT claims.

### Next records to add

- exact external commit hashes after cloning engines;
- pinned pattern corpus hashes;
- first correctness-adapter results;
- forum status audit for selected community targets.

## 2026-08-23 — engine setup: Golly 5.0 and BB-OPENCL operational (native Windows)

### Environment

- Windows 11 Home, native (no WSL distro, no MSVC, no CUDA toolkit installed at setup time).
- GPU: NVIDIA GeForce RTX 5070 Ti, 16 GiB VRAM, driver 610.47, compute capability 12.0, power limit 300 W.
- Rust 1.98.0 stable `x86_64-pc-windows-gnu` via rustup (GNU toolchain chosen because MSVC is absent).
- Repo validation on Python 3.14: 6 unit tests pass; `validate_results.py` reports 36 sources, 13 engines, 18 problems, 10 workloads, 0 results.

### Golly 5.0 (GOLLY-HASHLIFE / GOLLY-QUICKLIFE)

- Official `golly-5.0-win-64bit.zip`, SHA-256 `ec4e5a701023688de0c74aef1fc77f2c856f22a454baaa8f6efe86966cdfe2b8`.
- Installed at `E:\life-research\golly\golly-5.0-win-64bit\`; `bgolly.exe` SHA-256 `9632471133206e422cc73c02505f1014b6ffdb1e8fb6df6f0df5000446c46379`.
- Correctness: `bgolly -m 4` on the pinned `glider.rle` agrees exactly with `scripts/reference_life.py`; translation-normalised coordinate SHA-256 `303cc8533593ab9fd9318e787e8eee3d99d929b8039db37ef73bc8787c260ea3` on both sides.

### Binary Banter (BB-OPENCL)

- Clone: https://github.com/binary-banter/fast-game-of-life at commit `b7d743e3957c4bbfb1062d9b899bd17454c098fc` (2024-05-24), kept outside this repository at `E:\life-research\src\fast-game-of-life\`.
- Build: `cargo build --release --features opencl`; OpenCL import library generated from the NVIDIA driver's `OpenCL.dll` with mingw `gendef`/`dlltool` (no OpenCL SDK needed), linked via `RUSTFLAGS=-L native=E:\life-research\opencl-lib`.
- Correctness: the engine's own 26-test suite passes on the GPU (`CL_DEVICE_TYPE_GPU` explicitly requested) in 2.70 s.
- First informal throughput smoke measurement (criterion `step_1024`: bounded 65536×65536 grid, 1024 generations per iteration, 10 samples, process priority Idle): median 398.54 ms, range 398.14–398.89 ms → ≈1.10×10¹³ explicit cell updates/s. Same order as the authors' 2023 A40 CUDA figure (11.72×10¹²) and above their 7900 XTX OpenCL figure (8.94×10¹²). **Label: self-run smoke measurement** — not schema-conformant (no manifest, single pinned workload absent, no cold/warm split, GPU sync verified via the final in-order-queue event wait in `opencl.rs::step`).

### Deviations and follow-ups

- The environment doc assumes WSL2 Ubuntu; none is installed. lifelib, `gol_engines`, LSSS/LLSSS/ikpx2 need WSL2 (or substantial native porting) before Stage 2 items 2–3.
- BB-CUDA and CAT `PACK` need MSVC Build Tools plus CUDA toolkit ≥ 12.8 (Blackwell sm_120, `--gpu-architecture=native`). Decide WSL2-vs-native-CUDA before those builds.
- Next: wrap `bgolly` and a small BB CLI in `scripts/record_run.py` adapters and land the first schema-conformant sanity results.

## 2026-08-24 — first recorded results; BB-OPENCL boundary-leakage bug found and fixed

### First schema-conformant results (21 result files, all validating)

- **Golly 5.0 sanity + r-pentomino** (`2026-08-23__GOLLY-*`): block/blinker/glider states from QuickLife and HashLife match `scripts/reference_life.py` exactly (translation-normalised coordinate digests). r-pentomino at 50,000 generations: QuickLife, HashLife and the Python reference all give population 116 with identical normalised digests; the six escaped gliders sit at ±12,480 cells (c/4 diagonal), reference bbox [-12464,-12482,12484,12490].
- **Dense bounded-plane workloads** pinned in `benchmarks/workloads.csv` via the new `scripts/gen_dense_workload.py` (SplitMix64, one draw per cell; canonical raster digest convention shared bit-for-bit with the Rust adapter): `dense-plane-1024x2208-d31-s42` (pop 700,767) and `dense-plane-4096x4416-d31-s42` (pop 5,607,598). Input RLEs live in `D:\Programs\life-research\datasets\` (generated, not committed; SHA-256 pinned in workloads.csv).
- **BB-OPENCL** (`2026-08-24__BB-OPENCL__*`, RTX 5070 Ti, driver 610.47): 1024×2208 ×1000 gens, update 1.9–2.3 ms (≈1.1×10¹² CUPS; launch-overhead-bound at this size); 4096×4416 ×10000 gens, update 20.8–21.3 ms (≈8.6×10¹² CUPS). All repetitions bit-identical; adapter re-derives the input digest each run.
- **GOLLY-QUICKLIFE** on the 1024×2208 workload: ~0.9 s wall per cold run — QuickLife exploits the decaying activity, so this is not a CUPS-comparable number (as per methodology).
- Cross-engine agreement on 1024×2208 @ 1000: BB-OPENCL = BB-trivial (canonical digest `7c4b18d3…`, pop 96,689) = bgolly QuickLife (bbox-normalised content match; bgolly writes plain RLE without position, handled by `scripts/digest_bounded_rle.py --match-raster`).

### Found: multi-step boundary leakage in binary-banter/fast-game-of-life (OpenCL)

- Four-way pre-check (BB-OPENCL vs BB-trivial vs Python bounded reference vs bgolly, 64×736 universe) caught BB-OPENCL diverging from the other three: first divergence at **2** in-kernel generations, 4 differing cells all at x = 0.
- Root cause: the kernel evolves its padding halo (16 rows vertically, outer window halves horizontally) as live-capable space inside a 16-step launch; dead-boundary semantics were only restored between launches. Births leak into the padding and feed back within a launch. The engine's own tests miss it (patterns never touch edges; the equivalence-to-trivial test is CUDA-gated).
- Also characterised: the kernel writes back 736 rows per work group, so the simulated universe height is the request rounded up to a multiple of 736; buffer rows beyond write coverage are permanently dead.
- Fix: per-substep boundary masks (`adapters/bb-opencl/patches/0002-fix-boundary-leakage.patch`). Verified bit-exact against three independent implementations over 1–1000 generations. Throughput cost on 65536²×1024: 398.5 ms → 439.2 ms (11.03 → 10.01 ×10¹² CUPS, ≈10%); three mask variants measured within noise of each other.
- The CUDA kernel shares the design and likely the bug; unverified (no CUDA toolchain installed). Reported upstream 2026-08-24 with an edge-blinker minimal repro (dies in 2 generations on a bounded grid; buggy kernel resurrects it via a phantom birth at x = −1, verified failing at the pristine base commit): issue https://github.com/binary-banter/fast-game-of-life/issues/4, fix PR https://github.com/binary-banter/fast-game-of-life/pull/5 (kernel fix + regression test, 27/27 tests pass).
- Implication for the published 2023 CUPS figures: throughput claims are unaffected (interior-dominated), but exact bounded-plane correctness near edges was not what the unpatched engine computed; our recorded BB-OPENCL runs use the patched kernel (`engine_commit: b7d743e3+0001+0002`).

### New infrastructure

- All external installs relocated from `E:\life-research\` to `D:\Programs\life-research\` (Golly, engine clone, OpenCL import lib, builds, datasets); Rust toolchain moved to `D:\Programs\cargo` / `D:\Programs\rustup` with `CARGO_HOME`/`RUSTUP_HOME` persisted as user environment variables. Result JSONs recorded before the move retain the then-current `E:\` command paths.
- `adapters/bb-opencl/` — adapter crate (`bb_gol_bench`), patches, README with full reproduction steps.
- `scripts/gen_dense_workload.py`, `scripts/digest_bounded_rle.py` — pinned-workload generation and bounded-state digesting/matching.
- Verification conventions: canonical raster digest (universe-anchored) for engines with known placement; bbox-normalised content match for Golly's position-free RLE output.

## 2026-08-24 — gol_engines builds natively on Windows; 0E0P claims partially reproduced; GPU-port feasibility measured

### Native build (no WSL2 required)

- `das67333/gol_engines` at `9247f831` (v0.2.1) is pure Rust (tokio/ahash/flate2) and builds with the GNU toolchain after a **one-line fix**: the implicit autoref through a raw pointer in the `_mm_prefetch` call (`quadtree_sync/memory.rs`) became a hard error (`dangerous_implicit_autorefs`) on Rust 1.98. Patch: `adapters/gol-engines/patches/0001-fix-rust198-autoref.patch`; filed upstream as https://github.com/das67333/gol_engines/pull/5 (fork senegrom/gol_engines, branch fix/rust-1.98-autoref). All 31 tests pass.
- The full benchmark corpus ships in-repo (`res/very_large_patterns/`, incl. `0e0p-metaglider.mc.gz`), so the environment doc's WSL2 assumption is wrong for this engine; corrected scope: WSL2 remains relevant for lifelib/apgsearch/LSSS/ikpx2 only.

### 0E0P reproduction (reduced scale: 2^12 generations, 12 GiB tables, 6 cores vs the author's 2^14, ≥64 GiB, 32 cores)

- `stats` reproduces the upstream README exactly: hash `0xc322148cce4e1279`, population 93,235,805, 818,007 nodes, identical size distribution.
- `update --gens-log2=12` gives population **93,237,300** (the README value) on every engine variant and repetition; canonical output hash `0x02dda802a893049e` and even the output `.mc.gz` bytes are identical across engines and repetitions.
- Recorded (`2026-08-24__GOLENG-*`, workload `long-0e0p`): parallel HashLife (6 workers) update 63.6 / 66.0 s (r3 contaminated by concurrent builds, flagged in its JSON); single-threaded 329.9 s → **5.1× on 6 workers**, consistent with the author's ~10× on 24 workers; parallel StreamLife at 2^14: update 107.8 s, population 93,238,830, canonical hash `0xf65baa30355c3ff6`.
- Independent cross-check (r4): parallel HashLife at 2^14 (step-log2=12, GC-forced) reproduces the StreamLife state exactly — canonical hash `0xf65baa30355c3ff6`, population 93,238,830. HashLife and StreamLife agree bit-for-bit at 2^14.

### GPU-port feasibility (the "port it to GPU" question)

HashLife's structure determines the answer. The only offloadable dense arithmetic is the leaf base case (16×16 → 8×8, ≤4 generations, `update_leaves`); everything else is memoized-hashtable pointer chasing, and every unique leaf is computed once then cached, so leaf work is a one-time cost per unique configuration.

Measurements (branch `leaf-instr`, worktree `D:\Programs\life-research\src\goleng-instr`, kept GPL-side and out of this repo):

- `gpu_leaf_bench` (OpenCL, one leaf task per work item, bit-identical to CPU): CPU single core 6.31 M leaves/s (158.5 ns/leaf); RTX 5070 Ti end-to-end incl. PCIe: 4.4 M/s at batch 1k (launch-bound, ≈ CPU), 213 M/s at 64k, **peak ≈230 M/s at 512k**, 140 M/s at 4M (read-back-bound). GPU wins only when ≥ tens of thousands of independent leaf tasks can be batched per round trip — but the recursion produces them one at a time at memoization misses, so batching would require restructuring the engine around deferred leaf resolution.
- Instrumented single-threaded 0E0P run at 2^12 (same parameters as the clean 329.9 s recorded run; instrumented run's own wall time contaminated by concurrent jobs and not used): **21,488 leaf calls** total; 6 ms in leaf arithmetic, 11 ms in `update_leaves` including its hashtable insertion; population 93,237,300 ✓.

**Verdict: a GPU port of gol_engines' HashLife is not viable via leaf offload, with certainty.** Memoization leaves only ~21k unique leaf computations for the whole 2^12-generation 0E0P update — **≈0.003%** of the single-threaded 329.9 s. An infinitely fast GPU leaf path yields ≤1.0001× end-to-end (Amdahl); even the batching prerequisite (≥ tens of thousands of independent tasks per PCIe round trip, from the microbench) exceeds the total number of leaf tasks that exist. The remaining 99.997% is memoized-hashtable probing and node construction — latency-bound pointer chasing that PCIe-attached GPUs make worse, not better. This measured negative result settles research-report §11 idea 3 ("GPU leaf kernels for a quadtree engine") for HashLife-class engines on compressible patterns: the correct division of labour stands — HashLife-family on CPU for compressible workloads, dense GPU engines (BB-OPENCL, CAT) where every cell must be updated. A GPU HashLife would require moving the entire hashtable/recursion machinery on-device (a research programme, not a port), and the memoization profile gives it no arithmetic to win back.

## 2026-08-25 — Golly 5.0 joins the 0E0P row; Track B (four-row Garden of Eden) tooling started

### long-0e0p is now three-way cross-verified

- `2026-08-25__GOLLY-HASHLIFE__long-0e0p__r1..r3` (bgolly 5.0, HashLife, -M 12000): every rep reproduces canonical hash `0x02dda802a893049e` and population 93,237,300 — identical to all gol_engines variants. Three independent codebases (Golly 5.0, gol_engines HashLife sync/async, gol_engines StreamLife at 2^14 via r4) agree bit-for-bit on this workload.
- Wall times (cold, incl. load and .mc.gz save; bgolly reports no split): 206.9 / 205.7 s clean, r3 462.9 s contaminated (flagged). Same-machine comparison at 2^12: **gol_engines async (6 workers) wall 84–86 s < Golly 5.0 single-thread ~206 s < gol_engines single-thread 352 s.** Two notes against the author's 2^14 table (Golly 4.3: 848.5 s vs their sync 431.5 s): the parallel advantage reproduces (~2.4× over Golly here), but the single-thread ordering FLIPS — Golly 5.0 beats HashLifeEngineSync on this machine/scale, where Golly 4.3 lost to it on theirs. Golly 5.0 improvements, the 2^12-vs-2^14 regime, and the X3D cache are all candidate explanations; label self-run, reduced scale.

### Track B started: four-row Garden of Eden (LIFE-C001)

New tooling (all committed):

- `scripts/preimage_sat.py` — one-step preimage SAT checker (pysat; local orphan test with the exact +1-margin semantics). Validated **exhaustively** at 2×2 and 2×3 against brute-force enumeration of all preimage patches (zero mismatches, both over- and under-constraint directions exercised; returned patches re-verified by direct stepping). This is the independent certificate-checker for any orphan candidate. `tests/test_preimage_sat.py` (skips without pysat; CI stays stdlib-only).
- `scripts/goe4_transfer.py` + `tools/goe4_transfer/` (Rust) — column-transfer NFA formulation: states are pairs of (h+2)-bit preimage columns, h = 4+2d; a four-row orphan with d specified dead rows above/below exists iff the NFA (all states initial/final, 16-letter alphabet of image columns) is not universal. Any escaping word IS the orphan, cross-checkable by preimage_sat. d=0 must be universal (known no-height-4-orphan theorem) — the built-in validation target.

First findings (all self-run, 2026-08-25):

- **The σ-total-core shortcut fails: memoryless column extension does not exist.** Greatest-fixpoint cores are EMPTY at d=0 (349 of 4096 pair-states survive one round, none survive two) and d=1 (3559 of 65536, then none). Since d=0 is universal by the known theorem, height-4 image strips can always be extended column-by-column, but no single-run greedy strategy does it — lookahead over preimage-column subsets is essential. Nice structural fact about the height-4 extension property.
- **Both naive antichain directions blow up at d=0**: forward subset-BFS ~265k antichain members at word depth 6; backward maximal-bad fixpoint >312k elements (largest bad set 3114/4096 states) without converging in ~10 CPU-minutes. The exact universality re-proof (and the open d≥1 cases) need heavier machinery.
- Next options, in order: (1) simulation/bisimulation quotient of the NFA before subset analysis; (2) k-subset witness families (k=2 is ~8.4M pairs at d=0, feasible in Rust) — a nonempty closed family proves universality with a small certificate; (3) width-bounded 2QBF via a QBF solver (cf. marijnheule/eden's aztec instances, cloned to D:\Programs\life-research\src\eden); (4) width-bounded forward BFS for bounded negative results at d≥1.
- LifeWiki/conwaylife.com is behind Cloudflare bot protection (403 for both the wiki and pattern files) — known-Garden-of-Eden RLEs for an end-to-end UNSAT test of preimage_sat must come from another source (Golly's collection has none).

### Status recheck (per governance, community-dynamic problem)

Web audit 2026-08-25: Wade (June 2023) proved no height-4 orphans under the specified-cell definition — the d=0 validation target; Eker (April 2016) found a 5×83 Garden of Eden, so five live rows suffice and four is the exact frontier; the four-row live-cell question remains open in the searchable record. The Hartman/Heule "Symmetry in Gardens of Eden" line and marijnheule/eden's QBF instances confirm 2QBF is the expert-standard search method — our strip variant is the same machinery with a different existential region.

### Quotient/simulation attempt (negative), and the working QBF pipeline

- Bisimulation quotient of the d=0 transfer NFA: 4096 → 3025 classes (weak), and the simulation preorder on the quotient is **trivial** (zero non-reflexive pairs) — the standard antichain accelerators have nothing to grip; subset blowup resumed immediately. The NFA is structurally irreducible by these tools; `tools/goe4_transfer` retains the quotient+simulation `search` mode for the record.
- **CAQE 4.0.1 built natively on Windows** (D:\Programs\life-research\src\caqe + patched local cryptominisat-rs: CMake-4 policy env, `libcryptominisat5win.a` naming, `-lstdc++` link; details reproducible from the source trees). Verified on polarity smoke tests.
- `scripts/goe4_qbf.py` generates QDIMACS for the width-bounded orphan question, with a Quine–McCluskey-minimised Life biconditional (self-checked against all 512 neighbourhoods at import). Two forms: primal (∃P ∀X: no preimage) and **dual** (∀P ∃X: preimage exists; TRUE = no orphan with width ≤ w). CAQE struggles on the primal (timeout at d=0 w=2) but the dual works: d=0 w=2 in 0.9 s, w=4 in 32 s — both FALSE-orphan, matching Wade and matching direct enumeration (`E:\tmp-claude\brute_goe4.py` ground truth: 0 orphans at d=0 w≤3, d=1 w=2). Dual difficulty scales with the 4w-bit pattern space; practical ceiling ≈ w 5–7 per height at current settings.
- d=1 (the open shape) width sweep, dual form, 900 s per width: **no four-row orphan with one specified dead row above and below (height-6 window) exists with width ≤ 4** — w=2 in 6.8 s, w=3 in 6.9 s, w=4 in 109 s; w=5 exceeded 900 s (undecided). Together with the brute-force ground truth (d=1 w=2: 0 orphans among all 256 patterns) these are the first recorded width bounds specific to the open four-row live-cell question. Modest widths — Eker's five-row Garden of Eden is 83 wide, so the interesting regime is far beyond current QBF reach; scaling needs symmetry breaking in the pattern space (cf. Hartman/Heule), a better solver, or the per-height unbounded-width automaton route. Any TRUE-side find is decoded and independently verified by `preimage_sat` before being believed.
- Instances are reproducible from `scripts/goe4_qbf.py` (deterministic generation); the QDIMACS files themselves are not committed.

### k=2 witness family: also empty — Wade's theorem has witness complexity ≥ 3

`tools/goe4_transfer --mode pairs` computes the greatest closed family of witness sets of size ≤ 2 (family F closed iff every W ∈ F has, for every letter, some W' ∈ F inside succ(W); nonempty F ⟹ universal). At d=0: 8.4M pairs shrink 443,155 → 296 → **0** in three rounds (~70 s). Combined with the empty σ-total core (k=1), this shows the height-4 no-orphan theorem cannot be witnessed by any strategy tracking ≤ 2 candidate runs — **the extension property genuinely requires ≥ 3-way lookahead**, which is why the naive antichain constructions blow up. k=3 is ~10¹⁰ triples and needs a different representation; parked.

### Exact determinization: decisively infeasible (the experiment that closes the exact route)

`tools/goe4_transfer --mode determinize` ran the plain deterministic subset construction from the full state set at d=0 with hash-deduplication and a 16M-subset (7.6 GiB) cap: **cap hit** after 1,418,344 subsets explored of 15.9M discovered, with the fresh-subset frontier only at word length 7 and a sustained discovery/exploration ratio of ~11. The reachable deterministic subset count at height 4 is therefore far beyond 16M (plausibly 10⁸–10⁹⁺), and the d=1 automaton (16× more states, 8 KiB per subset) is hopeless by explicit enumeration on any near-term hardware. Combined with the trivial simulation preorder, the empty k≤2 witness families, and the antichain blowups, every standard finite-automata technique is now measured dead on this automaton: **per-height unbounded-width universality needs a genuinely new idea, not more compute.** The practical frontier for LIFE-C001 stays width-bounded QBF plus theory.

### Track A: the stream workload family lands — StreamLife's 36× shown same-machine

`scripts/gen_stream_workload.py` generates the long-planned antiparallel glider tapes (diagonal lanes, alternating directions, non-interacting by construction — so exact population 5N and cross-engine canonical-hash equality are built-in correctness oracles).

- **stream-synthetic-001** (periodic tape, 1024 gliders): both engines update 2^18 generations in ~0.1 s — an honest negative: a *periodic* tape is HashLife-trivial too (one glider period memoizes everything). Kept as a correctness-grade workload.
- **stream-synthetic-002-aperiodic** (8192 gliders, seeded aperiodic gaps breaking spatial periodicity): recorded update times over 3 cold reps each — **StreamLife 0.2 / 0.9 / 1.0 s vs HashLife 5.4 / 9.3 / 13.8 s**, i.e. a ~**10× median advantage** (range 5–40×; an uncontended-warmup HashLife run hit 36 s, so dispersion is high and both engines are cache-sensitive here). Identical canonical hash `0xc67e052976ab9055` and exact population 40,960 from every run of both engines. This is the first same-machine demonstration of StreamLife's specialty in the benchmark. Runs in `benchmarks/results/2026-08-26__GOLENG-*__stream-synthetic-*`.
- Side observation for upstream: RLE load dominates both engines on this workload (12–63 s across reps, ~150 s when contended, vs 0.2–14 s of update) — pattern/tree construction, not simulation, is the bottleneck; worth profiling upstream.

## 2026-08-26 — LIFE-F001 (Salo's padding constant): flip-point machinery, the GoE zoo has no witnesses, nine orphan verifications

Pivot to Life facts proper: attack on Q28820954 (optimal padding thickness, Salo–Törmä arXiv:1912.00692 Theorems 3/5).

**Formalisation.** For rectangular P, pad^c(P) is P with c specified dead rings; "admits a preimage" is exactly our +1-margin patch semantics (`preimage_sat.check_window`, verified against the paper's Section 2 definitions). Preimage existence is anti-monotone in c (a thicker padding's patch restricts to a thinner's), so each P has one flip point f(P) = least c with pad^c(P) an orphan (∞ if none), and Theorem 5 forces f(P) ∈ {0,1,2,3,4,∞}. **The open question equals: determine max finite f(P).** Known lower bound 1; any P with f(P) ≥ 2 improves it. `scripts/padding_flip.py` computes f (a few validated SAT calls per pattern); its `sanity` mode confirmed SAT@4 ⇒ SAT@5,6 on 200 random patterns (encoding consistent with the theorem).

**Exhaustive tiny sweeps.** Every nonempty pattern up to 3×3 (129 canonical under symmetry) has f = ∞ — no flips at all at these sizes, as expected: f ≥ 1 witnesses require pad^f(P) to be an orphan, and orphans are ≥ 11×9-scale.

**The known-GoE zoo route: closed.** Every published Garden of Eden we could obtain — Banks 1971 (33×9, pop 226), the 1991 14×14, Flammenkamp/Beluchenko-era 13×12, 12×11, 11×11s, the 11×10 and 11×9 records, the 45-cell 11×11, and the five-row 45×5 — has **f(P) = 0**: the bare bounding-box pattern is already an orphan (`scripts/verify_goe_zoo.py`, reproducible with pinned provenance from conwaylife.appspot.com; patterns are third-party and fetched, not committed). Consequences: (a) the paper's "at least 1" bound cannot be witnessed by bounding-box patterns of known GoEs — f ≥ 1 examples must be constructed; (b) as a by-product, the preimage checker's UNSAT path is now validated end-to-end against **nine independent published orphans** (previously flagged as a validation gap).

**Witness search, first ring: empty.** f(P) = 1 witnesses are equivalently orphans with an all-dead outer ring and a preimageable interior. The D4-symmetric enumeration of all 32,767 nonempty 9×9 cores inside 11×11 dead-ringed windows completed with **zero finds** (96 min): no D4-symmetric 11×11 orphan with a dead border ring exists at all — a clean bounded negative. Next rings (C4 at 9×9, D4 at 11×11 cores, ~2M candidates each) require the incremental-SAT template (window values as assumption literals on one persistent solver) rather than per-candidate CNF builds.

**Second rings (incremental engine, six parallel workers).**

- **C4 at 9×9: census complete and empty.** All 2,097,151 C4-symmetric 9×9 cores checked (~53 min wall across 3 workers): none has a dead-ringed 11×11 orphan padding. Combined with the D4-9×9 result: no rotationally symmetric 9×9-core dead-ringed orphan exists — consistent with the smallest known orphan bounding boxes (11×9 and up).
- **D4 at 11×11: census complete — 346 orphans, four padding witnesses, and a record-tying specimen** (`data/discoveries/d4-ring-orphans-11x11.txt`, all 346 re-verified by the slow checker, 0 mismatches):
  - **Four explicit f(P) = 1 witnesses** (populations 84, 73, 69, 69): bare 11×11 core preimageable, dead-ringed 13×13 window an orphan. These are, to our knowledge, the first explicit patterns witnessing that the Salo–Törmä padding constant is ≥ 1 — the paper states the bound without an example. Each is a Garden of Eden whose bounding-box pattern alone does not reveal it.
  - **A new 45-cell orphan with full D4 symmetry** — ties the smallest-known-orphan population (the zoo's 45-cell 11×11) and is NOT that pattern (verified distinct under all eight symmetries; the known one has no symmetry). Maximal symmetry at record population.
  - 342 of 346 are orphans bare (f = 0 cores); population spectrum 45–85 with heavy concentration at 61–69.
- Note: the incremental template's UNSAT path, unexercised in the all-SAT K=9 runs, is live-fire validated — every find re-checked by the slow exhaustively-validated encoding.
- **f = 2 at D4 11×11: complete and empty** (3 workers, ~5 h each): no D4-symmetric 11×11 core has pad¹ preimageable and pad² an orphan.
- **f = 2 at C4 9×9: complete and empty** (32 min). With D4-9×9 (empty census) this exhausts every enumerable small symmetric family: **no f ≥ 2 witness exists among rotationally symmetric cores up to 11×11.** The padding-constant lower bound stays at 1; raising it needs C4 11×11 (2³¹ candidates, ~2 weeks at current rates), 13×13 D4 (2²⁸), asymmetric SAT-guided search, or theory. Parked pending a decision on compute scale.
- **Single-flip neighborhood of the 346: complete** (41,866 candidates, 5.8 h): **60 additional verified f = 1 witnesses** (near-D4, populations 68–85; family now 64 total), 5,002 asymmetric dead-ringed orphans, minimum flip population 59 — the 45-cell specimen is a local minimum (no 44-cell orphan in its flip neighborhood).

### Symmetry breaking lands: ~6× on the dual QBF

`goe4_qbf.py --symmetry` restricts the ∀-pattern space to lex-leaders under the strip-preserving symmetry group {column reversal, row flip, 180°} via fully biconditional lex chains (sound: orphan-hood is invariant; verified d=0 w=2/w=4 answers unchanged, w=4 time 32 s → 5.6 s). d=0 w=6 still exceeds 600 s — the per-width wall moves about one width outward. The long-budget symmetric sweep completed 2026-08-26: **d=2 (height 8) no orphan with width ≤ 4** (w=2/3/4 in 97/84/169 s) — a new height row — plus **d=0 w=5 TRUE (57 min)** and **d=1 (height 6) no orphan with width ≤ 5 (35.5 min)**; d=1 w=6 exceeded its 2 h budget (undecided). Overnight runs on the two frontier cells (d=1 w=6 at 8 h, d=2 w=5 at 4 h) launched detached at idle priority.

Width table for the open shape (no orphan up to the stated width):

| dead rows d | window height | verified width bound | frontier |
|---|---|---|---|
| 0 | 4 | any width | Wade 2023; QBF re-verified ≤ 5 |
| 1 | 6 | ≤ 5 | w=6 undecided after a full 8 h budget — genuinely hard cell |
| 2 | 8 | ≤ 5 | confirmed on retry (49 min); w=6 next |

## 2026-08-28 — f ≥ 2 campaign launched; the f = 1 result written up

**`data/discoveries/f1-witness.md`** — standalone explainer for the f = 1 result: the pop-69 witness W with an explicit 13×13 preimage patch for its bare window (SAT model, independently re-stepped), the dead-ring orphan fact, precise definitions, the open-question framing (c* ∈ [1,4], W pins the 1), and a two-command re-verification recipe using only `preimage_sat.py`. All four D4 witnesses re-verified fresh for the document (bare SAT + verified patch, pad¹ UNSAT, flip_point = 1: 4/4).

**The f ≥ 2 hunt, resumed at the next rungs** (user green-light on compute scale). Two prongs, 12 detached Idle workers (launcher `D:\Programs\life-research\build\launch_f2_campaign.ps1`, outputs `f2deep13-w*.out` / `f2flips-*.out` alongside it; all workers affinity-pinned to cores 0–7 to leave four cores clear for an unrelated training job):

- **`scripts/f2_deep_search.py`** — reversed-order deep search over symmetric cores: one incremental pad² check per candidate (SAT = common exit), so only rare pad²-orphans pay further checks, and the pad¹ census at the size falls out as a byproduct. Finds classified f = 0 / 1 / 2; f1/f2 finds always slow-verified, first f0s spot-verified. **Validated on D4 11×11 span [1499800, 1506232): reproduces exactly the 14 known census entries with correct classes (13 f0 + the pop-69 f1), zero f2, all spot checks pass.**
- **Prong 1 — D4 13×13** (2²⁸ orbit-subsets, 8 workers in 2²⁵ chunks): simultaneously the first 13×13 ringed-orphan census, a new-f1-witness harvest, and the f ≥ 2 hunt. Dense-slice probe ~224/s/worker → roughly 2–3 days shared with the box's other load.
- **Prong 2 — `scripts/f2_flips.py`**: pad² status of every single (~42k) and double (~2.5M) flip of the 346 census orphans — asymmetric territory adjacent to deep orphans, invisible to any symmetric census, and never pad²-checked before (the earlier single-flip sweep classified pad¹ only). Instances sit at the SAT/UNSAT boundary and are measurably harder: singles ~17/s, doubles ~148/s. 1+3 workers, ~2 h expected.
- Rung choice: D4 13×13 costs ~8× less total solver work than C4 11×11 (2²⁸ × ~1.5 vs 2³¹) and opens a new size class; C4 11×11 stays queued behind it.

### 2026-08-28 (late) — flip prong complete: 1,080 new witnesses, still no f = 2; the 13×13 landscape is far richer

- **Flip neighbourhoods DONE** — all 2,553,826 single+double flip variants of the 346-member census pad²-checked:
  - depth 1 (41,866 variants): f0 = 5,002, f1 = 60, f2 = 0 — *exactly* reproduces the earlier single-flip sweep's totals through independent code (cross-validation), and adds the new fact: no f = 2 among singles.
  - depth 2 (2,511,960 variants): f0 = 60,048 asymmetric double-flip ringed orphans, **f1 = 1,080 new witnesses** (first 60 slow-verified; the shared incremental template is validated by the exact depth-1 reproduction), **f2 = 0**. The f1-rich members cluster hard: the [115,230) member range alone held 764 of the 1,080.
  - The witness family grows 64 → **1,144+** in one evening.
- **Deep 13×13 at ~14%** (workers at 60–101/s under shared load): **21,831 D4 13×13 ringed orphans, 586 D4-symmetric f1 witnesses so far** — versus 346 and 4 in the entire 11×11 family: both phenomena scale up superlinearly with size. Every f1 slow-verified; **zero f2 candidates, zero mismatches**. Populations 65–121. Revised completion estimate ~3–4 days.
- Session restart killed the watch task; re-armed with a tighter filter (F2/MISMATCH/DONE/stalls only — f1 finds are now routine events tracked by counts).

### 2026-08-28 (later) — boundary attack: single flips of every known f = 1 witness

- New `scripts/f2_witness_flips.py`. Rationale: f = 1 witnesses are pad¹-boundary-critical (bare SAT, one ring UNSAT), so their single-flip neighbourhoods are the most f=2-likely territory we know — and none of it is covered by prior sweeps: single flips of double-flip witnesses are *triple* flips of census members, and the 13×13 witnesses' neighbourhoods are untouched. The script harvests witnesses from campaign outputs (1,076 distinct 11×11 double-flip witnesses; a 648-witness 13×13 snapshot), re-checks each is genuinely f = 1, then per variant runs pad¹ first (UNSAT = cheap exit) and pad² for survivors, slow-verifying any candidate.
- First boundary-geometry measurement: **~92% (11×11) / ~81% (13×13) of witness single-flips restore pad¹ SAT** — witness orphan-hood is single-cell fragile, exactly the regime where pad¹ and pad² could decouple into an f = 2.
- 4 workers launched at idle/pinned (~130k + ~109k boundary variants, a few hours). The 13×13 pass is a snapshot; rerun after the deep campaign for late witnesses.

### 2026-08-30 — deep census throttled to 2 cores with rolling resume

- Per user request the census now uses only cores 0–1: 6 of 8 workers killed cleanly, each `.out` carrying a `DONE-PARTIAL` marker with its exact resume point; ~168M candidates queued in `build\f2deep13-queue.txt` (w3b…w8b). A detached Idle driver (`build\f2deep13-driver.ps1`, log `f2deep13-driver.log`) keeps exactly 2 workers running until the queue drains — survives session restarts. ETA at 2 cores ≈ 2.5 weeks; overlap re-checks at resume boundaries are harmless duplicates (harvests dedup by raster).
- Boundary sweep (13×13 witness single-flips): ~95% complete (witnesses 308/324 and 296/324), f2 = 0 so far; per-instance cost ~100× the 11×11 sweep — the hardest SAT instances of the campaign.

### 2026-08-30 — boundary prong complete: 232,217 witness perturbations, pad¹/pad² never decouple

Single-flip sweep of every known f = 1 witness finished:

| size | witnesses | variants | pad¹ restored SAT | f2 |
|---|---|---|---|---|
| 11×11 | 1,076 | 122,705 | 105,259 (85.8%) | **0** |
| 13×13 | 648 | 109,512 | 94,453 (86.2%) | **0** |

In 232,217 single-cell perturbations of pad¹-boundary-critical patterns, every variant whose pad¹ window regained a preimage also had a preimageable pad² window — **the two padding depths never once decoupled**, even at the sharpest known boundary. Combined with the exhaustive symmetric censuses and the 2.55M-variant census flip sweep (all f2 = 0), this is real evidence that either the Salo–Törmä constant is exactly 1, or f = 2 witnesses require structure qualitatively different from near-orphan perturbations. The 13×13 instances averaged ~2 s of solver time each (~12.6 h/worker) — near-boundary SAT is two orders harder than bulk census SAT.

Remaining active prong: the 2-core driver-managed D4 13×13 deep census (~82% to go). Next design candidates if that stays empty: GPU-prefiltered census at C4 11×11 / D4 15×15, or double-flip witness neighbourhoods with a GPU front-end.
