"""Modal fan-out for the small-population C4 11x11 orphan census (record hunt).

    modal run modal/c4_census_modal.py --max-j 11 --containers 120
    modal run modal/c4_census_modal.py --max-j 3 --containers 2 --smoke 1   (tiny)

Candidates: j-subsets of the 30 size-4 C4 orbits (j <= max_j) times centre
on/off, in lexicographic rank order, split into rank ranges. Fat containers:
8 worker processes each, one task list per container. Finds (pad^1 orphans)
are returned with their rasters; anything with population < 45 is a new
smallest known Garden of Eden.
"""

from __future__ import annotations

import json
import time
from math import comb
from pathlib import Path

import modal

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
BUILD = Path(r"D:\Programs\life-research\build")
CPUS = 8

app = modal.App("conway-c4-census")
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("python-sat")
    .add_local_dir(str(SCRIPTS), remote_path="/root/scripts")
)


def _worker(task):
    j, centre, rank_start, rank_end = task
    import sys
    sys.path.insert(0, "/root/scripts")
    from c4_orphan_census import search_range
    logs: list[str] = []
    r = search_range(j, centre, rank_start, rank_end, log=logs.append)
    r["log"] = logs
    return r


@app.function(image=image, cpu=float(CPUS), memory=CPUS * 1536, timeout=6 * 3600, max_containers=150)
def run_tasks(tasks: list) -> dict:
    from multiprocessing import Pool
    with Pool(min(CPUS, len(tasks))) as pool:
        results = pool.map(_worker, tasks)
    return {"checked": sum(r["checked"] for r in results),
            "finds": [f for r in results for f in r["finds"]],
            "log": [line for r in results for line in r["log"]],
            "seconds": max(r["seconds"] for r in results)}


def make_tasks(max_j: int, task_size: int, smoke: int = 0):
    tasks = []
    for j in range(max_j + 1):
        total = comb(30, j)
        for centre in (0, 1):
            start = 0
            while start < total:
                end = min(total, start + task_size)
                tasks.append((j, centre, start, end))
                start = end
    if smoke:
        tasks = tasks[:smoke * CPUS]
    return tasks


@app.local_entrypoint()
def main(max_j: int = 11, containers: int = 120, task_size: int = 100_000, smoke: int = 0):
    tasks = make_tasks(max_j, task_size, smoke)
    total = sum(e - s for _, _, s, e in tasks)
    per = max(1, (len(tasks) + containers - 1) // containers)
    per = max(per, CPUS)  # each container gets at least one task per worker
    jobs = [tasks[i:i + per] for i in range(0, len(tasks), per)]
    print(f"c4 census: max_j={max_j}, {total} candidates in {len(tasks)} tasks over {len(jobs)} containers "
          f"x {CPUS} workers", flush=True)
    t0 = time.time()
    checked = 0
    finds = []
    done = 0
    for r in run_tasks.map(jobs, order_outputs=False):
        done += 1
        checked += r["checked"]
        finds += r["finds"]
        for line in r["log"]:
            print(line, flush=True)
        if done % 10 == 0 or r["finds"]:
            print(f"  {done}/{len(jobs)} containers, {checked} checked, {len(finds)} orphans, "
                  f"min pop {min([f['pop'] for f in finds], default=None)}, {time.time() - t0:.0f}s", flush=True)
    out = BUILD / f"modal-c4census-j{max_j}{'-smoke' if smoke else ''}.json"
    out.write_text(json.dumps({"max_j": max_j, "checked": checked, "finds": finds}, indent=1), encoding="utf-8")
    pops = sorted(f["pop"] for f in finds)
    print(f"DONE modal c4census max_j={max_j}: checked {checked}, orphans {len(finds)}, "
          f"populations {pops[:10]}{'...' if len(pops) > 10 else ''}, {time.time() - t0:.0f}s -> {out}", flush=True)
