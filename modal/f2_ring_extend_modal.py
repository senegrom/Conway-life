"""Modal fan-out for the ring-extension f = 2 search (scripts/f2_ring_extend.py).

Local entrypoint harvests the rigid 13x13 cores from the census outputs on
this PC, splits them into chunks, and maps search_chunk over Modal CPU
containers (1 core each). Results (finds, stats) are collected locally and
written to D:/Programs/life-research/build/modal-ringext-<mode>.json.

    modal run modal/f2_ring_extend_modal.py --mode w11 --chunks 60
Containers are fat: CPUS cores each, one worker process per core, so each
container does minutes of solid work instead of seconds (startup overhead and
idle time were dominating the one-core layout).
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


CPUS = 8  # cores per container; one worker process per core


def _merge(results: list[dict]) -> dict:
    """Sum numeric fields, concatenate lists, across per-process results."""
    out: dict = {}
    for r in results:
        for k, v in r.items():
            if isinstance(v, (int, float)) and k not in ("start", "end", "chunk"):
                out[k] = out.get(k, 0) + v
            elif isinstance(v, list):
                out.setdefault(k, []).extend(v)
            else:
                out[k] = v
    return out


def _split(items: list, parts: int) -> list[list]:
    size = (len(items) + parts - 1) // parts
    return [items[i * size:(i + 1) * size] for i in range(parts) if items[i * size:(i + 1) * size]]


def _search_worker(args):
    cores, k, rings, classify = args
    import sys
    sys.path.insert(0, "/root/scripts")
    from f2_ring_extend import search
    logs: list[str] = []
    r = search(cores, 0, len(cores), k=k, quiet=True, log=logs.append, rings=rings, classify=classify)
    r["log"] = logs
    return r


def _flip_worker(args):
    rasters, k, gen2, sample_mod, residues = args
    import sys
    sys.path.insert(0, "/root/scripts")
    from f2_flip_search import flip_search, gen2_attack
    logs: list[str] = []
    if gen2:
        r = gen2_attack(rasters, k=k, sample_mod=sample_mod, log=logs.append, residues=residues)
    else:
        r = flip_search(rasters, k=k, log=logs.append)
    r["log"] = logs
    return r


@app.function(image=image, cpu=float(CPUS), memory=CPUS * 1536, timeout=6 * 3600, max_containers=60)
def search_chunk(chunk: dict) -> dict:
    """One fat container: the chunk's cores split over CPUS worker processes."""
    from multiprocessing import Pool
    parts = _split(chunk["cores"], CPUS)
    with Pool(len(parts)) as pool:
        results = pool.map(_search_worker, [(p, chunk["k"], chunk.get("rings", 1), chunk.get("classify", False)) for p in parts])
    r = _merge(results)
    r["chunk"] = chunk["id"]
    return r


@app.function(image=image, cpu=float(CPUS), memory=CPUS * 1536, timeout=6 * 3600, max_containers=120)
def flip_chunk(chunk: dict) -> dict:
    from multiprocessing import Pool
    parts = _split(chunk["rasters"], CPUS)
    with Pool(len(parts)) as pool:
        results = pool.map(_flip_worker, [(p, chunk["k"], chunk.get("gen2", False), chunk.get("sample_mod", 10),
                                           tuple(chunk.get("residues", (0,)))) for p in parts])
    r = _merge(results)
    r["chunk"] = chunk["id"]
    return r


def ring_rasters(cores_by_label: dict, witnesses, k: int, rings: int):
    """Reconstruct full rasters of (label, rbits) witnesses."""
    import sys
    sys.path.insert(0, str(SCRIPTS))
    from f2_ring_extend import ring_orbits
    rorb = ring_orbits(k, rings)
    n = k + 2 * rings
    out = []
    for label, rbits in witnesses:
        core = cores_by_label[label]
        raster = [[0] * n for _ in range(n)]
        for i in range(k):
            for j in range(k):
                raster[i + rings][j + rings] = core[i][j]
        for idx, o in enumerate(rorb):
            if rbits >> idx & 1:
                for i, j in o:
                    raster[i][j] = 1
        out.append((f"{label}+ring{rbits}", raster))
    return out


def harvest_local(k: int, mode: str) -> list[tuple[str, list[list[int]]]]:
    """Cores: mode f0/f1/all -> 13x13 census cores; mode w11 -> all known
    11x11 f = 1 witnesses (4 D4 census + 60 single-flip + 1,076 double-flip)."""
    import sys
    sys.path.insert(0, str(SCRIPTS))
    if mode == "w11":
        from f2_two_ring_anchored import harvest_11
        return harvest_11()
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
def main(mode: str = "f0", chunks: int = 60, start: int = 0, end: int = -1, k: int = 13,
         rings: int = 1):
    if mode == "flip15":
        return flip_main(chunks, start, end)
    if mode == "gen2rest":   # the 90% not covered by the gen210 sample (hash residues 1..9)
        return flip_main(chunks, start, end, gen2=True, sample_mod=10, residues=tuple(range(1, 10)))
    if mode.startswith("gen2"):
        return flip_main(chunks, start, end, gen2=True, sample_mod=int(mode[4:] or 10))
    classify = mode.endswith("c")
    if classify:
        mode = mode[:-1]
    if mode == "w11":
        k, rings = 11, 2
    cores = harvest_local(k, mode)
    if end < 0 or end > len(cores):
        end = len(cores)
    cores = cores[start:end]
    n = len(cores)
    chunks = max(1, min(chunks, n))
    size = (n + chunks - 1) // chunks
    jobs = [{"id": i, "k": k, "rings": rings, "classify": classify,
             "cores": cores[i * size:(i + 1) * size]}
            for i in range(chunks) if cores[i * size:(i + 1) * size]]
    from f2_ring_extend import ring_orbits
    nrings = 1 << len(ring_orbits(k, rings))
    print(f"mode={mode}: {n} cores x {nrings} ring configs = {n * nrings} candidates in {len(jobs)} chunks "
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
    if classify:
        wl = [w for r in results for w in r["witnesses"]]
        f0 = sum(r["f0"] for r in results); f1 = sum(r["f1"] for r in results)
        wf = BUILD / f"witnesses{k + 2 * rings}-{mode}.json"
        wf.write_text(json.dumps({"k": k, "rings": rings, "f0": f0, "f1": f1,
                                  "witnesses": wl}), encoding="utf-8")
        print(f"classified: f0 (bare orphans) {f0}, f1 (witnesses) {f1} -> {wf}", flush=True)
    out = BUILD / f"modal-ringext-{mode}-{start}-{end}.json"
    out.write_text(json.dumps({"mode": mode, "k": k, "start": start, "end": end,
                               "candidates": tot_c, "pad1_sat": tot_p, "f2": tot_f2,
                               "finds": [f for r in results for f in r["finds"]],
                               "mismatches": [m for r in results for m in r["mismatches"]],
                               "chunks": [{kk: v for kk, v in r.items() if kk not in ("log",)} for r in results]},
                              indent=1), encoding="utf-8")
    print(f"DONE modal ringext {mode} [{start},{end}): candidates {tot_c}, pad1-SAT {tot_p}, "
          f"f2={tot_f2}, {time.time() - t0:.0f}s -> {out}", flush=True)


def flip_main(chunks: int, start: int, end: int, gen2: bool = False, sample_mod: int = 10,
              residues=(0,)):
    """Single-flip boundary attack on the 15x15 witnesses produced by mode w11c;
    with gen2=True, the second-generation attack on a 1/sample_mod sample of
    their f = 1 single-flip variants (mode gen2<N>, e.g. gen210 = 10%)."""
    wf = BUILD / "witnesses15-w11.json"
    data = json.loads(wf.read_text(encoding="utf-8"))
    k, rings = data["k"], data["rings"]
    cores_by_label = dict(harvest_local(k, "w11"))
    rasters = ring_rasters(cores_by_label, [tuple(w) for w in data["witnesses"]], k, rings)
    if end < 0 or end > len(rasters):
        end = len(rasters)
    rasters = rasters[start:end]
    n = len(rasters)
    chunks = max(1, min(chunks, n))
    size = (n + chunks - 1) // chunks
    jobs = [{"id": i, "k": k + 2 * rings, "rasters": rasters[i * size:(i + 1) * size],
             "gen2": gen2, "sample_mod": sample_mod, "residues": list(residues)}
            for i in range(chunks) if rasters[i * size:(i + 1) * size]]
    tag = f"gen2 (residues {sorted(residues)} mod {sample_mod})" if gen2 else "flip15"
    print(f"{tag}: {n} parent witnesses x {(k + 2 * rings) ** 2} flips in {len(jobs)} chunks", flush=True)
    t0 = time.time()
    results = []
    tot = ({"gen2": 0, "sampled": 0, "variants": 0, "pad1_sat": 0, "f2": 0} if gen2
           else {"variants": 0, "pad1_sat": 0, "f1": 0, "f2": 0})
    for r in flip_chunk.map(jobs, order_outputs=False):
        results.append(r)
        for key in tot:
            tot[key] += r[key]
        for line in r["log"]:
            print(line, flush=True)
        if len(results) % 20 == 0 or r["f2"]:
            print(f"  {len(results)}/{len(jobs)} chunks, {tot}, {time.time() - t0:.0f}s", flush=True)
    name = (f"gen2-{sample_mod}" + ("" if tuple(residues) == (0,) else "-r" + "".join(map(str, sorted(residues))))) if gen2 else "flip15"
    out = BUILD / f"modal-{name}-{start}-{end}.json"
    payload = {"totals": tot, "finds": [f for r in results for f in r["finds"]],
               "mismatches": [m for r in results for m in r["mismatches"]]}
    if gen2:
        payload["gen2_ids"] = [g for r in results for g in r["gen2_ids"]]
    out.write_text(json.dumps(payload), encoding="utf-8")
    print(f"DONE modal {name} [{start},{end}): {tot}, {time.time() - t0:.0f}s -> {out}", flush=True)
