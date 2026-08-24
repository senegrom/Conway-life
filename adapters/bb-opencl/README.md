# BB-OPENCL adapter (binary-banter/fast-game-of-life)

Benchmark adapter for the dense bounded-plane GPU engine registered as
`BB-OPENCL` in `data/engine-registry.csv`.

## Layout

- `bb_gol_bench/` — Rust CLI wrapping the engine: deterministic SplitMix64
  fill, timed init/update/readback, canonical raster digests, optional raster
  dump and raster-file input. One JSON line on stdout.
- `patches/` — local patches applied to the external engine clone:
  - `0001-bulk-buffer-access.patch` — adds `buffer_dims`, `paddings`,
    `simulation_rows`, `read_buffer_words`, `write_buffer_words` to
    `src/opencl.rs` (per-cell `get`/`set` do one blocking PCIe transfer each,
    which is unusable at benchmark sizes).
  - `0002-fix-boundary-leakage.patch` — **correctness fix** to
    `src/kernels/gol.cl`, found 2026-08-24 during cross-engine verification.

## The boundary-leakage bug (patch 0002)

The kernel simulates 16 generations per launch in local memory. The visible
universe is surrounded by padding (16 rows vertically; the outer half of the
16-cell staggered windows horizontally) that is zero in global memory, but the
multi-step loop evolved those padding cells like ordinary cells. Intermediate
generations could therefore give birth into the padding and leak back into the
visible universe before the launch ended: the dead-boundary condition was only
enforced between launches, not inside one.

Consequences before the fix:

- any in-kernel step count ≥ 2 diverged from the trivial reference for
  patterns whose activity touches the universe edge (first observed as a
  4-cell diff at x = 0 after 2 generations of a dense random fill);
- the engine's own test suite does not catch it: all its patterns stay away
  from the edges, and the `*_equivalent_trivial` test is compiled only for
  the CUDA feature. The CUDA kernel uses the same design and likely has the
  same bug (unverified here — no CUDA toolchain on this machine).

The fix precomputes per-thread row/edge masks and forces every out-of-universe
cell dead after each substep. Cost on the 65536²×1024 criterion benchmark
(RTX 5070 Ti): 398.5 ms → 439.2 ms, i.e. 11.03→10.01 ×10¹² cell updates/s
(≈10%). Verified bit-exact against BB-trivial, a Python bounded-plane
reference, and Golly 5.0 QuickLife on a 64×736 universe over 1–1000
generations, and against BB-trivial and QuickLife on the pinned
`dense-plane-1024x2208-d31-s42` workload.

A second subtlety the adapter accounts for: the kernel writes back
`simulation_rows()` (= 736 with shipped settings) rows per work group, so the
true simulated universe height is the requested height rounded up to a
multiple of 736 (width: multiple of 32). Rows inside the padded buffer beyond
that coverage are never updated and behave as outside-universe cells. Pinned
workloads use exact dimensions (1024×2208, 4096×4416) so requested = simulated.

## Reproducing the build

```powershell
git clone https://github.com/binary-banter/fast-game-of-life D:\Programs\life-research\src\fast-game-of-life
git -C D:\Programs\life-research\src\fast-game-of-life checkout b7d743e3957c4bbfb1062d9b899bd17454c098fc
git -C D:\Programs\life-research\src\fast-game-of-life apply <this-dir>\patches\0001-bulk-buffer-access.patch
git -C D:\Programs\life-research\src\fast-game-of-life apply <this-dir>\patches\0002-fix-boundary-leakage.patch

# OpenCL import library from the installed driver (no OpenCL SDK required);
# gendef/dlltool from any mingw-w64 distribution:
mkdir D:\Programs\life-research\opencl-lib; cd D:\Programs\life-research\opencl-lib
gendef C:\Windows\System32\OpenCL.dll
dlltool -d OpenCL.def -l libOpenCL.dll.a -D OpenCL.dll -m i386:x86-64

$env:RUSTFLAGS = "-L native=D:\Programs\life-research\opencl-lib"
$env:CARGO_TARGET_DIR = "D:\Programs\life-research\build\bb_gol_bench"   # keep target/ off OneDrive
cargo build --release --manifest-path bb_gol_bench\Cargo.toml
```

`bb_gol_bench/Cargo.toml` points at the engine clone with a machine-specific
path; adjust it if the clone lives elsewhere. Built with Rust 1.98.0
`x86_64-pc-windows-gnu` (no MSVC needed).

## Digest convention

SHA-256 over an ASCII raster of the full universe: one `'0'`/`'1'` per cell,
rows terminated by `\n`. Identical in `scripts/gen_dense_workload.py` (which
also emits the RLE input for other engines) and the adapter; every adapter run
recomputes the input digest so a cross-language PRNG or packing drift fails
loudly. Golly output for bounded universes is plain RLE without a position
line, so it is compared by bounding-box-normalised content instead
(`scripts/digest_bounded_rle.py --match-raster`).

## Example

```powershell
bb_gol_bench.exe --width 1024 --height 2208 --density-ppm 310000 --seed 42 `
    --gens 1000 --engine opencl
# {"engine":"opencl", ... "output_raster_sha256":"7c4b18d3...","output_population":96689, ...}
```
