"""Modal analysis for the narrowest five-row orphan question.

  modal run modal/goe5_analysis_modal.py --mode subwindows   # is any contiguous sub-window of the 45x5 orphan an orphan?
  modal run modal/goe5_analysis_modal.py --mode trajectory   # reachable-set sizes along the 45x5 orphan's columns
  modal run modal/goe5_analysis_modal.py --mode antichain --depth 30 --height 5
        exact depth-capped search: BFS over reachable state sets, keeping only
        inclusion-minimal sets (a superset can never be emptied earlier than a
        subset), until the empty set appears (= narrowest orphan of that
        height) or the depth cap / size cap is hit (= rigorous lower bound).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import modal

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
BUILD = Path(r"D:\Programs\life-research\build")

app = modal.App("conway-goe5-analysis")
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("python-sat", "numpy")
    .add_local_dir(str(SCRIPTS), remote_path="/root/scripts")
)


@app.function(image=image, cpu=4.0, memory=16384, timeout=3 * 3600)
def subwindows(rows: list[str]) -> dict:
    import sys
    sys.path.insert(0, "/root/scripts")
    from preimage_sat import check_window
    raster = [[int(c) for c in r] for r in rows]
    h, w = len(raster), len(raster[0])
    full, _ = check_window(raster)
    orphans = []
    checked = 0
    for width in range(1, w):
        for x0 in range(0, w - width + 1):
            sub = [r[x0:x0 + width] for r in raster]
            checked += 1
            sat, _ = check_window(sub)
            if not sat:
                orphans.append({"x0": x0, "width": width})
    return {"full_is_orphan": not full, "sub_checked": checked, "narrower_orphans": orphans}


@app.function(image=image, cpu=4.0, memory=16384, timeout=3 * 3600)
def trajectory(rows: list[str]) -> dict:
    import sys
    sys.path.insert(0, "/root/scripts")
    import numpy as np
    from goe5_beam import build_valid, step
    raster = [[int(c) for c in r] for r in rows]
    h, w = len(raster), len(raster[0])
    valid = build_valid(h)
    n = 1 << (h + 2)
    S = np.ones((n, n), dtype=bool)
    sizes = []
    for x in range(w):
        L = sum(raster[i][x] << i for i in range(h))
        S = step(S, valid[L])
        sizes.append(int(S.sum()))
    return {"sizes": sizes, "final": sizes[-1]}


@app.function(image=image, cpu=8.0, memory=96 * 1024, timeout=12 * 3600)
def antichain(height: int, depth: int, size_cap: int) -> dict:
    """Depth-capped exact search over reachable sets with subset-minimality pruning."""
    import sys
    sys.path.insert(0, "/root/scripts")
    import numpy as np
    from goe5_beam import build_valid, step
    h = height
    valid = build_valid(h)
    n = 1 << (h + 2)
    letters = 1 << h
    start = np.ones((n, n), dtype=bool)
    frontier = {start.tobytes(): (start, [])}
    log = []
    t0 = time.time()
    for d in range(1, depth + 1):
        nxt = {}
        for key, (S, word) in frontier.items():
            for L in range(letters):
                T = step(S, valid[L])
                if not T.any():
                    return {"orphan_width": d, "word": word + [L], "log": log,
                            "seconds": round(time.time() - t0)}
                k = T.tobytes()
                if k not in nxt:
                    nxt[k] = (T, word + [L])
        # antichain pruning: drop sets that are supersets of another set at this depth
        items = sorted(nxt.values(), key=lambda t: int(t[0].sum()))
        packed = [np.packbits(S.ravel()) for S, _ in items]
        keep = []
        keep_packed = []
        for (S, word), p in zip(items, packed):
            dominated = False
            for q in keep_packed:
                if np.array_equal(p & q, q):  # q subset of p -> p dominated
                    dominated = True
                    break
            if not dominated:
                keep.append((S, word))
                keep_packed.append(p)
        frontier = {S.tobytes(): (S, word) for S, word in keep}
        sizes = [int(S.sum()) for S, _ in keep]
        log.append(f"depth {d}: {len(nxt)} distinct sets, {len(keep)} minimal, smallest {min(sizes)}, "
                   f"{round(time.time() - t0)}s")
        if len(keep) > size_cap:
            return {"orphan_width": None, "stopped": "size cap", "depth_reached": d, "log": log,
                    "seconds": round(time.time() - t0)}
    return {"orphan_width": None, "stopped": "depth cap", "depth_reached": depth, "log": log,
            "seconds": round(time.time() - t0)}


@app.local_entrypoint()
def main(mode: str = "subwindows", height: int = 5, depth: int = 30, size_cap: int = 200000):
    rows = [l.strip() for l in (BUILD / "eker5x45.txt").read_text().split("\n") if l.strip()]
    if mode == "subwindows":
        r = subwindows.remote(rows)
        print(f"45x5 orphan confirmed: {r['full_is_orphan']}; sub-windows checked: {r['sub_checked']}; "
              f"narrower orphan sub-windows: {r['narrower_orphans']}", flush=True)
    elif mode == "trajectory":
        r = trajectory.remote(rows)
        print("reachable-set sizes along the 45 columns:", r["sizes"], flush=True)
    elif mode == "antichain":
        r = antichain.remote(height, depth, size_cap)
        for line in r["log"]:
            print(line, flush=True)
        if r["orphan_width"]:
            print(f"*** NARROWEST ORPHAN height {height}: width {r['orphan_width']} word {r['word']}", flush=True)
        else:
            print(f"no orphan of height {height} up to depth {r['depth_reached']} ({r['stopped']}), {r['seconds']}s", flush=True)
        (BUILD / f"modal-goe{height}-antichain.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    print("DONE goe5 analysis", mode, flush=True)
