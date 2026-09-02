"""Modal runner for scripts/goe5_beam.py (narrow fixed-height orphans).

    modal run modal/goe5_beam_modal.py --validate 300                 # NFA vs SAT cross-check
    modal run modal/goe5_beam_modal.py --height 5 --beam 300 --seeds 16 --max-width 46
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import modal

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
BUILD = Path(r"D:\Programs\life-research\build")

app = modal.App("conway-goe5-beam")
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("python-sat", "numpy")
    .add_local_dir(str(SCRIPTS), remote_path="/root/scripts")
)


@app.function(image=image, cpu=2.0, memory=8192, timeout=6 * 3600, max_containers=64)
def run_beam(args: dict) -> dict:
    import random
    import sys
    sys.path.insert(0, "/root/scripts")
    import numpy as np
    from goe5_beam import build_valid, beam_search, beam_prefix, good_set, mirror_letters, step, word_to_window
    from preimage_sat import check_window
    h = args["height"]
    valid = build_valid(h)
    logs: list[str] = []
    rng = random.Random(args["seed"])
    if args.get("suffix") is not None:
        suffix = args["suffix"]
        t0 = time.time()
        letters = mirror_letters(h) if args.get("mirror") else None
        prefix = beam_prefix(h, valid, suffix, args["beam"], args["max_prefix"], rng, log=logs.append,
                             noise=args.get("noise", 0.0), letters_allowed=letters)
        out = {"seed": args["seed"], "suffix_len": len(suffix), "seconds": round(time.time() - t0),
               "log": logs, "orphan": None}
        if prefix is not None:
            word = prefix + suffix
            window = word_to_window(word, h)
            sat, _ = check_window(window)
            out["orphan"] = {"width": len(word), "prefix_len": len(prefix), "word": word,
                             "rows": ["".join(map(str, r)) for r in window], "sat_confirms": (not sat)}
        return out
    if args.get("validate"):
        n = 1 << (h + 2)
        bad = 0
        for _ in range(args["validate"]):
            w = rng.randint(1, 6)
            word = [rng.randrange(1 << h) for _ in range(w)]
            S = np.ones((n, n), dtype=bool)
            for L in word:
                S = step(S, valid[L])
            sat, _ = check_window(word_to_window(word, h))
            if bool(S.any()) != sat:
                bad += 1
        return {"seed": args["seed"], "validate": args["validate"], "bad": bad, "log": logs}
    t0 = time.time()
    word = beam_search(h, valid, args["beam"], args["max_width"], rng, log=logs.append,
                       noise=args.get("noise", 0.0))
    out = {"seed": args["seed"], "beam": args["beam"], "height": h, "seconds": round(time.time() - t0),
           "log": logs, "orphan": None}
    if word is not None:
        window = word_to_window(word, h)
        sat, _ = check_window(window)
        out["orphan"] = {"width": len(word), "word": word, "rows": ["".join(map(str, r)) for r in window],
                         "sat_confirms": (not sat)}
    return out


@app.local_entrypoint()
def main(height: int = 5, beam: int = 300, seeds: int = 16, max_width: int = 46, noise: float = 0.15,
         validate: int = 0, suffix_len: int = 0, mirror: int = 0):
    if validate:
        r = run_beam.remote({"height": height, "seed": 1, "validate": validate})
        print(f"validate height {height}: {r['validate']} windows, disagreements {r['bad']}", flush=True)
        r4 = run_beam.remote({"height": 4, "seed": 2, "validate": validate})
        print(f"validate height 4: {r4['validate']} windows, disagreements {r4['bad']}", flush=True)
        return
    if suffix_len:
        rows = [l.strip() for l in (BUILD / "eker5x45.txt").read_text().splitlines() if l.strip()]
        raster = [[int(c) for c in r] for r in rows]
        w = len(raster[0])
        cols = [sum(raster[i][x] << i for i in range(height)) for x in range(w)]
        suffix = cols[w - suffix_len:]
        jobs = [{"height": height, "beam": beam, "max_prefix": max_width - suffix_len, "seed": s,
                 "noise": (0.0 if s == 0 else noise), "suffix": suffix, "mirror": mirror} for s in range(seeds)]
        print(f"prefix search against Eker's last {suffix_len} columns: beam {beam}, {seeds} seeds, "
              f"max prefix {max_width - suffix_len}, mirror-symmetric letters only: {bool(mirror)}", flush=True)
    else:
        jobs = [{"height": height, "beam": beam, "max_width": max_width, "seed": s, "noise": (0.0 if s == 0 else noise)}
                for s in range(seeds)]
        print(f"beam search: height {height}, beam {beam}, {seeds} seeds, max width {max_width}", flush=True)
    best = None
    results = []
    for r in run_beam.map(jobs, order_outputs=False):
        results.append(r)
        o = r["orphan"]
        if o:
            print(f"*** ORPHAN height {height} width {o['width']} seed {r['seed']} "
                  f"(SAT confirms: {o['sat_confirms']}) in {r['seconds']}s", flush=True)
            for row in o["rows"]:
                print("   " + row, flush=True)
            if best is None or o["width"] < best["width"]:
                best = o
        else:
            print(f"  seed {r['seed']}: no orphan up to width {max_width} ({r['seconds']}s); last: {r['log'][-1] if r['log'] else ''}", flush=True)
    out = BUILD / f"modal-goe{height}-beam{beam}{'-suffix' + str(suffix_len) if suffix_len else ''}{'-mirror' if mirror else ''}.json"
    out.write_text(json.dumps({"height": height, "beam": beam, "results": results}, indent=1), encoding="utf-8")
    print(f"DONE goe{height} beam: best width {best['width'] if best else None} -> {out}", flush=True)
