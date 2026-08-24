# gol_engines adapter notes

Native Windows build and reproduction record for
[das67333/gol_engines](https://github.com/das67333/gol_engines)
(engine IDs `GOLENG-HASH-ASYNC`, `GOLENG-HASH-ST`, `GOLENG-STREAM-ASYNC`).

Contrary to the environment doc's assumption, **no WSL2 is needed**: the crate
is pure Rust (tokio, ahash, flate2) and builds with the GNU toolchain.

## Build

```powershell
git clone https://github.com/das67333/gol_engines D:\Programs\life-research\src\gol_engines
git -C D:\Programs\life-research\src\gol_engines checkout 9247f831a2ddeaadd77e118daae7f839208b4e4e
git -C D:\Programs\life-research\src\gol_engines apply <this-dir>\patches\0001-fix-rust198-autoref.patch
$env:CARGO_TARGET_DIR = "D:\Programs\life-research\build\gol_engines"
cargo build --release --bin gol_engines_cli --features=cli_deps
```

`patches/0001-fix-rust198-autoref.patch`: one-line fix — the implicit autoref
through a raw pointer in `quadtree_sync/memory.rs` (`_mm_prefetch` argument)
became a hard error (`dangerous_implicit_autorefs`) on Rust 1.98. Candidate
for an upstream PR. The full test suite (31 tests) passes with it.

The benchmark corpus ships in the repo (`res/very_large_patterns/`, including
`0e0p-metaglider.mc.gz`).

## Reproduction status (2026-08-24, Ryzen 5 7500X3D 6C/12T, 31 GiB)

Reduced scale versus the author's 32-core / 96 GiB benchmark: 2^12 generations
with 12 GiB tables (the author's headline is 2^14 with >= 64 GiB).

- `stats` on 0E0P reproduces the README exactly: hash `0xc322148cce4e1279`,
  population 93,235,805, 818,007 nodes with identical size distribution.
- `update --gens-log2=12` reproduces population **93,237,300** (README value)
  on every run and engine variant; canonical output hash `0x02dda802a893049e`
  is identical across repetitions and engines (`gol_engines_cli stats` on the
  saved state; the `.mc.gz` byte hash is NOT expected to be stable across
  parallel runs, so result JSONs' state-file sha256 may differ per rep).
- Timings live in `benchmarks/results/2026-08-24__GOLENG-*`; the
  parallel-vs-single-threaded ratio on 6 cores is the locally meaningful
  number, not the author's cloud figures.

## GPU-port feasibility experiment

A `leaf-instr` branch (worktree `D:\Programs\life-research\src\goleng-instr`,
kept local, GPL-3.0 like upstream) instruments `update_leaves` and adds
`gpu_leaf_bench`, an OpenCL microbenchmark of the leaf arithmetic
(16x16 -> 8x8, 4 generations, one work item per leaf; bit-identical to CPU).
Findings and the port verdict are recorded in the research log.
