# Modal apps

Cloud fan-out for the searches in `scripts/`. Each app mounts `scripts/` into a
`debian-slim` image with `python-sat` (plus `numpy` where needed) and runs the
same functions used locally, so results are directly comparable.

Run them with the Modal CLI (any environment that has `modal` installed and a
configured profile):

```bash
modal run modal/<app>.py --help          # arguments of the local entrypoint
```

| App | What it does |
|---|---|
| `f2_ring_extend_modal.py` | Ring extensions and boundary attacks for the padding-constant hunt. Modes: `f0`/`f1`/`all` (13×13 cores), `w11` (11×11 witnesses + two rings), `w11c` (same, classifying the results into orphans and f = 1 witnesses), `flip15` (single-flip attack on the 15×15 witnesses), `gen2<N>` (second-generation attack on a 1/N sample), `gen2rest` (the complementary 90%). |
| `c4_census_modal.py` | Small-population C4 11×11 orphan census (the 45-cell record question). |
| `goe5_beam_modal.py` | Beam search for narrow fixed-height orphans, including suffix-anchored prefix search and exact endgame lookahead. |
| `goe5_exact_modal.py` | Exact BFS over reachable state sets: rigorous "no orphan of width ≤ W" bounds. |
| `goe_lower_bound_modal.py` | Polynomial certificates (k-lookback) for the same bounds. |
| `goe5_analysis_modal.py` | Analysis of Eker's 45×5 orphan: sub-window minimality, reachable-set trajectory, antichain search. |
| `cpu_probe_modal.py` | Diagnostic: verifies that a `cpu=N` container really runs N worker processes in parallel. |

Containers are deliberately **fat** (8 cores, one worker process per core):
one-core containers doing seconds of work were dominated by startup and idle
time. Modal's per-function CPU trace shows a single container, not the sum over
containers — use the probe app if the total looks too low.

Results are written to the local `build` directory named in each app; the
findings that matter are copied into `data/discoveries/` and summarised in
`docs/research-log.md`.
