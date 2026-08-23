# Benchmarks

## Principles

- Workload families are analysed separately.
- Inputs are content-addressed.
- Output correctness is mandatory.
- Raw run JSON is committed.
- Initialization and update time are separated where possible.
- Self-benchmarks remain labelled until independently reproduced.

## Result workflow

1. Add and pin a workload in `workloads.csv`.
2. Compute its SHA-256.
3. Run a small correctness case.
4. Use `scripts/record_run.py`.
5. Run `scripts/validate_results.py`.
6. Run `scripts/summarize_results.py`.
7. Commit raw JSON and generated tables.

## External pattern files

Do not copy third-party pattern collections without checking their licence. Record provenance and a content hash. Macrocell files can be very large; use a release asset or object store where necessary and retain a small manifest in Git.

## Result naming

```text
benchmarks/results/<date>__<engine-id>__<workload-id>__r<repetition>.json
```

## Planned adapters

- Golly headless script;
- lifelib C++ and Python wrappers;
- `gol_engines` CLI;
- Binary Banter benchmark binary;
- CAT test harness;
- apgsearch upload-disabled batch mode.

Adapters must output or retain a final state that can be hashed.
