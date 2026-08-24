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
