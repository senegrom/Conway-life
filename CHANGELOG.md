# Changelog

## Unreleased

- Golly 5.0 and Binary Banter OpenCL (BB-OPENCL) installed and verified on native Windows; setup provenance in the research log.
- First 21 schema-conformant benchmark results: Golly sanity + r-pentomino (50k generations, cross-verified against the reference engine) and dense bounded-plane runs.
- New pinned dense workloads `dense-plane-1024x2208-d31-s42` and `dense-plane-4096x4416-d31-s42` with `scripts/gen_dense_workload.py` and `scripts/digest_bounded_rle.py`.
- `adapters/bb-opencl/`: benchmark adapter for binary-banter/fast-game-of-life plus local patches, including a fix for a multi-step boundary-leakage correctness bug found during cross-engine verification (reported upstream: issue #4, PR #5).
- `adapters/gol-engines/`: native Windows build of das67333/gol_engines (one-line Rust-1.98 build fix), 0E0P reproduction at reduced scale, and a GPU-offload feasibility study of HashLife leaf updates.
- Golly 5.0 HashLife recorded on `long-0e0p`: three-way cross-engine agreement (Golly, gol_engines HashLife, StreamLife) on canonical state hash and population.
- Track B started (four-row Garden of Eden, LIFE-C001): `scripts/preimage_sat.py` (exhaustively validated preimage/orphan SAT checker + tests), `scripts/goe4_transfer.py` and `tools/goe4_transfer/` (column-transfer universality search; first structural findings in the research log).

## 0.1.0 — 2026-08-23

- Initial simulator landscape.
- Dated formal and community open-problem register.
- Publication and community workflow.
- Benchmark methodology and result schema.
- Pure-Python Life reference implementation.
- Benchmark recorder, validator and summary generator.
- Initial issue briefs and CI.
