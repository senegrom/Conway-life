# Changelog

## Unreleased

- Golly 5.0 and Binary Banter OpenCL (BB-OPENCL) installed and verified on native Windows; setup provenance in the research log.
- First 21 schema-conformant benchmark results: Golly sanity + r-pentomino (50k generations, cross-verified against the reference engine) and dense bounded-plane runs.
- New pinned dense workloads `dense-plane-1024x2208-d31-s42` and `dense-plane-4096x4416-d31-s42` with `scripts/gen_dense_workload.py` and `scripts/digest_bounded_rle.py`.
- `adapters/bb-opencl/`: benchmark adapter for binary-banter/fast-game-of-life plus local patches, including a fix for a multi-step boundary-leakage correctness bug found during cross-engine verification (reported upstream: issue #4, PR #5).

## 0.1.0 — 2026-08-23

- Initial simulator landscape.
- Dated formal and community open-problem register.
- Publication and community workflow.
- Benchmark methodology and result schema.
- Pure-Python Life reference implementation.
- Benchmark recorder, validator and summary generator.
- Initial issue briefs and CI.
