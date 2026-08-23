# Simulator landscape

**Last checked:** 2026-08-23

## The workload taxonomy

A useful benchmark must identify four independent axes:

1. **State representation:** bounded dense array, sparse tiles, hashed quadtree.
2. **Temporal behaviour:** chaotic, locally stable, periodic, recursively repeated.
3. **Geometry:** finite plane, unbounded plane, torus, other boundary.
4. **Objective:** one final state, every intermediate state, object census, or constraint search.

A claim of “X cells per second” is meaningful only when the algorithm explicitly updates those cells. HashLife may skip immense space-time volumes, so its result belongs on a wall-time/memory curve rather than a CUPS leaderboard.

## Engine matrix

| Engine | Core method | Best regime | Weak regime | Evidence |
|---|---|---|---|---|
| Golly HashLife | memoized hashed quadtree | extremely long regular evolution | chaotic patterns | mature official implementation |
| Golly QuickLife | conventional non-hashing | ordinary/chaotic interactive evolution | astronomical generation jumps | mature official implementation |
| lifelib `pattern` | generated leaves + HashLife | programmable regular evolution | no multicore lifetree | mature library/community use |
| lifelib StreamLife | directional two-universe HashLife | separated antiparallel streams | ordinary patterns | specialised mature implementation |
| lifelib `upattern` | overlapping active tiles | random patterns, torus, soup work | recursive long-time repetition | mature library/community use |
| `gol_engines` async | parallel HashLife/StreamLife | large recursive workloads with parallel subproblems | small patterns | promising author benchmark, needs reproduction |
| Binary Banter CUDA | bit packing + temporal blocking + `LOP3` | dense bounded radius-1 Life | sparse/unbounded/HashLife workloads | open source, author benchmark |
| CAT `PACK` | packet-coded CUDA | dense bounded low-radius CA | long compressible patterns | peer-reviewed comparison |
| CAT tensor cores | matrix accumulation | large-neighbourhood CA | standard radius-1 Life relative to `PACK` | peer reviewed |
| apgsearch | tile/CPU + CUDA screening | distributed random soup census | arbitrary one-off large pattern | community production system |
| CAX | JAX/XLA | batched/general/differentiable CA | not established as pure-Life record engine | peer-reviewed general library |

## Performance numbers that must not be merged into one chart

### `gol_engines`

Author-reported 0E0P metaglider benchmark:

| Algorithm/work | Implementation | Update seconds |
|---|---|---:|
| HashLife, \(2^{14}\) generations | `gol_engines` async | 41.7 |
| HashLife, \(2^{14}\) generations | Golly 4.3 | 848.5 |
| HashLife, \(2^{14}\) generations | lifelib | 912.1 |
| StreamLife, \(2^{27}\) generations | `gol_engines` async | 186.9 |
| StreamLife, \(2^{27}\) generations | lifelib | 991.1 |

Treat as a reproduction target. It is one machine, one pattern, author code, and older comparator versions.

### Binary Banter

Author-reported dense CUPS:

| Hardware | Engine | CUPS |
|---|---|---:|
| NVIDIA A40 | CUDA | \(11.720\times10^{12}\) |
| NVIDIA V100 | CUDA | \(9.871\times10^{12}\) |
| NVIDIA 2080 Ti | CUDA | \(9.666\times10^{12}\) |
| AMD 7900 XTX | OpenCL | \(8.939\times10^{12}\) |
| Intel i9-11900K | multithreaded SIMD CPU | \(296.019\times10^9\) |

These are explicit dense updates and are not comparable to HashLife generation jumps.

### CAT

The CAT paper's key crossover is algorithmic:

- radius 1–2: tensor cores are competitive, but the fastest packet-coded approach wins;
- radius 3 and above: CAT increasingly wins;
- at large radius: up to roughly 14× over the fastest competing approach in the authors' tests.

For Conway Life, reproduce `PACK` before pursuing tensor cores.

## Benchmark hypotheses

H1. Golly/lifelib HashLife wins on regular patterns until memory pressure or parallel recursion becomes dominant.

H2. `gol_engines` wins on sufficiently large decomposable recursive workloads but not small patterns.

H3. Binary Banter or CAT `PACK` wins dense toroidal radius-1 tests on the RTX GPU.

H4. QuickLife or a CPU bit-parallel engine can beat GPU execution at small sizes due to launch and transfer overhead.

H5. apgsearch throughput is determined by the full GPU-filter/CPU-census pipeline, not the kernel alone.

H6. A simple workload classifier based on active density, tile churn and node-reuse rate can predict the best engine.

## Source links

- Golly: https://golly.sourceforge.io/
- HashLife help: https://golly.sourceforge.io/Help/Algorithms/HashLife.html
- QuickLife help: https://golly.sourceforge.io/Help/Algorithms/QuickLife.html
- lifelib: https://gitlab.com/apgoucher/lifelib
- lifelib overview: https://conwaylife.com/wiki/Lifelib
- `gol_engines`: https://github.com/das67333/gol_engines
- Binary Banter: https://github.com/binary-banter/fast-game-of-life
- CAT: https://arxiv.org/abs/2406.17284
- apgsearch: https://conwaylife.com/wiki/Apgsearch
