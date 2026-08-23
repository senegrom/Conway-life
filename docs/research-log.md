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
