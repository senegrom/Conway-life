"""Diagnostic: verify that a cpu=8 Modal container really runs 8 worker
processes in parallel. Each worker spins a fixed CPU-bound loop; the wall
time of 8 parallel workers vs 1 worker gives the effective parallelism.
    modal run modal/cpu_probe_modal.py
"""
import os
import time

import modal

app = modal.App("conway-cpu-probe")
image = modal.Image.debian_slim(python_version="3.12")


def _spin(n: int) -> float:
    t = time.perf_counter()
    x = 0
    for i in range(n):
        x = (x * 1103515245 + i) & 0xFFFFFFFF
    return time.perf_counter() - t


@app.function(image=image, cpu=8.0, memory=4096, timeout=600)
def probe(workers: int) -> dict:
    from multiprocessing import Pool
    n = 20_000_000
    t = time.perf_counter()
    with Pool(workers) as pool:
        per = pool.map(_spin, [n] * workers)
    wall = time.perf_counter() - t
    aff = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None
    return {"workers": workers, "wall_s": round(wall, 2), "per_worker_s": [round(p, 2) for p in per],
            "os_cpu_count": os.cpu_count(), "affinity_cpus": aff,
            "cgroup_cpu_max": open("/sys/fs/cgroup/cpu.max").read().strip() if os.path.exists("/sys/fs/cgroup/cpu.max") else None}


@app.local_entrypoint()
def main():
    r1 = probe.remote(1)
    r8 = probe.remote(8)
    r16 = probe.remote(16)
    print("1 worker :", r1)
    print("8 workers:", r8)
    print("16 workers:", r16)
    speedup = r8["workers"] * r1["wall_s"] / r8["wall_s"]
    print(f"effective parallel speedup with 8 workers: {speedup:.1f}x (ideal 8x)")
