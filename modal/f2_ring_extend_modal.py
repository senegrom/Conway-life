"""Modal fan-out for the ring-extension f = 2 search (scripts/f2_ring_extend.py).

Local entrypoint harvests the rigid 13x13 cores from the census outputs on
this PC, splits them into chunks, and maps search_chunk over Modal CPU
containers (1 core each). Results (finds, stats) are collected locally and
written to D:/Programs/life-research/build/modal-ringext-<mode>.json.

    modal run modal/f2_ring_extend_modal.py --mode f0 --chunks 300
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import modal

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
BUILD = Path(r"D:\Programs\life-research\build")

app = modal.App("conway-f2-ringext")
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("python-sat")
    .add_local_dir(str(SCRIPTS), remote_path="/root/scripts")
)


@app.function(image=image, cpu=1.0, memory=2048, timeout=3 * 3600, max_containers=300)
def search_chunk(chunk: dict) -> dict:
    import sys
    sys.path.insert(0, "/root/scripts")
    from f2_ring_extend import search
    logs: list[str] = []
    r = search(chunk["cores"], 0, len(chunk["cores"]), k=chunk["k"], quiet=True,
               log=logs.append)
    r["chunk"] = chunk["id"]
    r["log"] = logs
    return r


def harvest_local(k: int, mode: str) -> list[tuple[str, list[list[int]]]]:
    """Same harvest as scripts/f2_ring_extend.harvest_cores, without importing
    it locally (the local Modal venv has no pysat)."""
    import sys
    sys.path.insert(0, str(SCRIPTS))
    from ring_orphan_search import cell_orbits
    orbits = cell_orbits(k, "d4")
    cores = {}
    for f in sorted(BUILD.glob(f"f2deep{k}-*.out")):
        t = f.read_text(encoding="utf-8")
        for m in re.finditer(r"^RINGED-ORPHAN bits=(\d+) pop=(\d+)", t, re.M):
            bits = int(m.group(1))
            raster = [[0] * k for _ in range(k)]
            for idx, o in enumerate(orbits):
                if bits >> idx & 1:
                    for i, j in o:
                        raster[i][j] = 1
            cores[bits] = ("f0", raster)
        pat = r"F1-WITNESS \(slow-verified\) bits=(\d+) pop=\d+ core=%d group=d4\n((?:[01]{%d}\n){%d})" % (k, k, k)
        for m in re.finditer(pat, t):
            cores[int(m.group(1))] = ("f1", [[int(c) for c in row] for row in m.group(2).split()])
    out = [(f"{kind}:{bits}", r) for bits, (kind, r) in sorted(cores.items())]
    if mode != "all":
        out = [c for c in out if c[0].startswith(mode)]
    return out


@app.local_entrypoint()
def main(mode: str = "f0", chunks: int = 300, start: int = 0, end: int = -1, k: int = 13):
    cores = harvest_local(k, mode)
    if end < 0 or end > len(cores):
        end = len(cores)
    cores = cores[start:end]
    n = len(cores)
    chunks = max(1, min(chunks, n))
    size = (n + chunks - 1) // chunks
    jobs = [{"id": i, "k": k, "cores": cores[i * size:(i + 1) * size]}
            for i in range(chunks) if cores[i * size:(i + 1) * size]]
    rings = 256
    print(f"mode={mode}: {n} cores x {rings} rings = {n * rings} candidates in {len(jobs)} chunks "
          f"(~{size} cores each)", flush=True)
    t0 = time.time()
    results = []
    tot_c = tot_p = tot_f2 = 0
    for r in search_chunk.map(jobs, order_outputs=False):
        results.append(r)
        tot_c += r["candidates"]; tot_p += r["pad1_sat"]; tot_f2 += r["f2"]
        for line in r["log"]:
            print(line, flush=True)
        if len(results) % 20 == 0 or r["f2"]:
            print(f"  {len(results)}/{len(jobs)} chunks, {tot_c} candidates, pad1-SAT {tot_p}, "
                  f"f2 {tot_f2}, {time.time() - t0:.0f}s", flush=True)
    out = BUILD / f"modal-ringext-{mode}-{start}-{end}.json"
    out.write_text(json.dumps({"mode": mode, "k": k, "start": start, "end": end,
                               "candidates": tot_c, "pad1_sat": tot_p, "f2": tot_f2,
                               "finds": [f for r in results for f in r["finds"]],
                               "mismatches": [m for r in results for m in r["mismatches"]],
                               "chunks": [{kk: v for kk, v in r.items() if kk not in ("log",)} for r in results]},
                              indent=1), encoding="utf-8")
    print(f"DONE modal ringext {mode} [{start},{end}): candidates {tot_c}, pad1-SAT {tot_p}, "
          f"f2={tot_f2}, {time.time() - t0:.0f}s -> {out}", flush=True)
