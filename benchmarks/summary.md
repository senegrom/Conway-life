# Benchmark summary

Generated from raw JSON. Workload families must be interpreted separately.

| Workload | Engine | Runs | OK | Median s | Min s | Max s | Median RSS bytes |
|---|---|---:|---:|---:|---:|---:|---:|
| dense-plane-1024x2208-d31-s42 | BB-OPENCL | 3 | 3 | 0.374738 | 0.361826 | 0.419706 |  |
| dense-plane-1024x2208-d31-s42 | GOLLY-QUICKLIFE | 3 | 3 | 0.884673 | 0.881748 | 0.928599 |  |
| dense-plane-4096x4416-d31-s42 | BB-OPENCL | 3 | 3 | 2.498375 | 2.302146 | 2.799331 |  |
| long-0e0p | GOLENG-HASH-ASYNC | 4 | 4 | 128.141199 | 83.851249 | 241.898553 |  |
| long-0e0p | GOLENG-HASH-ST | 1 | 1 | 351.836315 | 351.836315 | 351.836315 |  |
| long-0e0p | GOLENG-STREAM-ASYNC | 1 | 1 | 135.814975 | 135.814975 | 135.814975 |  |
| long-0e0p | GOLLY-HASHLIFE | 3 | 3 | 206.917352 | 205.663238 | 462.856108 |  |
| sanity-blinker | GOLLY-HASHLIFE | 1 | 1 | 0.014091 | 0.014091 | 0.014091 |  |
| sanity-blinker | GOLLY-QUICKLIFE | 1 | 1 | 0.023945 | 0.023945 | 0.023945 |  |
| sanity-block | GOLLY-HASHLIFE | 1 | 1 | 0.013508 | 0.013508 | 0.013508 |  |
| sanity-block | GOLLY-QUICKLIFE | 1 | 1 | 0.121924 | 0.121924 | 0.121924 |  |
| sanity-glider | GOLLY-HASHLIFE | 1 | 1 | 0.012295 | 0.012295 | 0.012295 |  |
| sanity-glider | GOLLY-QUICKLIFE | 1 | 1 | 0.021760 | 0.021760 | 0.021760 |  |
| sparse-rpentomino | GOLLY-HASHLIFE | 3 | 3 | 0.017285 | 0.016944 | 0.018205 |  |
| sparse-rpentomino | GOLLY-QUICKLIFE | 3 | 3 | 0.044509 | 0.042338 | 0.050545 |  |
| stream-synthetic-001 | GOLENG-HASH-ASYNC | 1 | 1 | 28.166546 | 28.166546 | 28.166546 |  |
| stream-synthetic-001 | GOLENG-STREAM-ASYNC | 1 | 1 | 21.680569 | 21.680569 | 21.680569 |  |
| stream-synthetic-002-aperiodic | GOLENG-HASH-ASYNC | 3 | 3 | 31.215833 | 25.207854 | 33.374150 |  |
| stream-synthetic-002-aperiodic | GOLENG-STREAM-ASYNC | 3 | 3 | 68.330556 | 20.174465 | 109.638508 |  |
