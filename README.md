# Conway Life Open Research

A reproducible research workspace for Conway's Game of Life (B3/S23), focused on:

1. benchmarking high-performance simulators without comparing incompatible workloads;
2. maintaining a dated, sourced register of genuinely open questions;
3. running verifiable computational searches;
4. publishing discoveries through the appropriate community and academic channels.

**Research snapshot:** 2026-08-23  
**Status:** initial landscape review and experimental design  
**Rule:** no record or theorem claim is accepted without a reproducible artefact and a verification path.

## Central conclusion

There is no single meaningful “fastest Game of Life simulator.”

- **Very long, compressible evolution:** HashLife is the first choice.
- **Antiparallel glider-stream constructions:** StreamLife can be dramatically faster.
- **Random soups:** lifelib's tile-based machinery and apgsearch are designed for this regime.
- **Huge dense or chaotic bounded grids:** bit-packed CUDA/OpenCL or SIMD engines dominate because HashLife cannot exploit enough repetition.
- **Open-pattern searches:** use specialised search programs such as LSSS, LLSSS, ikpx2, CatForce or SAT/SMT encodings, not a general-purpose simulator.

See [`RESEARCH_REPORT.md`](RESEARCH_REPORT.md) for the full assessment.

## Recommended first programme

Run two tracks in parallel.

### Track A — reproducible simulator benchmark

Build a workload-stratified benchmark comparing:

- Golly 5.0: HashLife and QuickLife;
- lifelib: HashLife, StreamLife and tile-based evolution;
- `gol_engines`: single-threaded and parallel HashLife/StreamLife;
- Binary Banter's dense CUDA/OpenCL implementation;
- CAT's packet-coded and tensor-core methods;
- apgsearch for soup throughput.

This fills a real infrastructure gap: the available performance claims use different patterns, boundaries, generation counts and hardware.

### Track B — Garden-of-Eden / preimage search

Start with two explicit questions:

- Can a Garden of Eden have all live cells restricted to four consecutive rows?
- What is the exact optimal zero-padding thickness in the Salo–Törmä padding theorem?

The route is SAT/SMT plus independently checkable certificates. A negative bounded result is useful when the exact search space and certificate are published.

## Repository map

```text
.
├── RESEARCH_REPORT.md
├── docs/
│   ├── research-log.md          # dated narrative of every campaign
│   ├── simulator-landscape.md
│   ├── open-problems.md
│   ├── benchmark-methodology.md
│   ├── community-and-publication.md
│   ├── research-roadmap.md
│   ├── environment-windows-wsl2.md
│   └── drafts/                  # unpublished write-ups (forum post)
├── data/
│   ├── discoveries/             # verified first-party results (see its README)
│   ├── engine-registry.csv
│   ├── open-problems.csv
│   ├── sources.csv
│   └── references.bib
├── scripts/                     # searches, checkers and analysis (Python)
├── modal/                       # cloud fan-out for the same searches (see its README)
├── tools/                       # Rust helpers (four-row transfer automaton)
├── adapters/                    # patches and harnesses for external engines
├── benchmarks/
│   ├── README.md
│   ├── workloads.csv
│   ├── benchmark-schema.json
│   ├── run_manifest.example.json
│   ├── patterns/
│   └── results/
├── issues/
├── tests/
└── .github/
```

## Local validation

The repository uses only the Python standard library.

```bash
python -m unittest discover -s tests
python scripts/validate_results.py
```

To record a benchmark command:

```bash
python scripts/record_run.py \
  --engine-id GOLLY-HASHLIFE \
  --workload-id sanity-glider \
  --generations 1024 \
  --result benchmarks/results/example.json \
  --state-file output.rle \
  -- your-command --and --arguments
```

Then produce a compact table:

```bash
python scripts/summarize_results.py
```

## Evidence labels

- **author-current:** listed as open on an author's maintained page.
- **paper-open:** explicitly asked in a primary paper.
- **community-dynamic:** a current record/search target; it may change without a paper.
- **needs-recheck:** useful lead whose status must be reconfirmed before spending compute.
- **self-benchmark:** performance reported by the engine author, not independently reproduced here.
- **peer-reviewed:** evaluated in a scholarly publication.

## Citation and licensing

Code is MIT-licensed. Research notes are CC BY 4.0. See `CITATION.cff`, `LICENSE`, and `LICENSE-DOCS.md`.
