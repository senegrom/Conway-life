"""Modal runner for scripts/goe_lower_bound.py (polynomial-time width bounds).

    modal run modal/goe_lower_bound_modal.py --heights 4,5 --k 1
    modal run modal/goe_lower_bound_modal.py --heights 5 --k 2
"""

from __future__ import annotations

import json
from pathlib import Path

import modal

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
BUILD = Path(r"D:\Programs\life-research\build")

app = modal.App("conway-goe-lower-bound")
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("python-sat", "numpy")
    .add_local_dir(str(SCRIPTS), remote_path="/root/scripts")
)


@app.function(image=image, cpu=8.0, memory=64 * 1024, timeout=6 * 3600)
def bound(args: dict) -> dict:
    import sys
    sys.path.insert(0, "/root/scripts")
    import numpy as np
    from goe5_beam import build_valid, mirror_letters, step
    from goe_lower_bound import fixed_point, fixed_point_indexed, verify_certificate
    height, k, max_iter, mirror = args["height"], args["k"], args["max_iter"], args["mirror"]
    valid = build_valid(height)
    if k == 0:
        r = fixed_point(height, max_iter, mirror, log=lambda s: print(s, flush=True), valid=valid)
        if r.get("no_orphan_any_width"):
            n = 1 << (height + 2)
            letters = mirror_letters(height) if mirror else list(range(1 << height))
            C = np.ones((n, n), dtype=bool)
            for _ in range(r["stabilised_at"]):
                nxt = C.copy()
                for L in letters:
                    nxt &= step(C, valid[L])
                C = nxt
            r["certificate_verified"] = verify_certificate(C, valid, letters)
    else:
        r = fixed_point_indexed(height, k, max_iter, mirror, log=lambda s: print(s, flush=True),
                                valid=valid)
    return r


@app.local_entrypoint()
def main(heights: str = "4,5", k: int = 1, max_iter: int = 200, mirror: int = 0):
    hs = [int(x) for x in heights.split(",") if x.strip()]
    jobs = [{"height": h, "k": k, "max_iter": max_iter, "mirror": bool(mirror)} for h in hs]
    results = []
    for h, r in zip(hs, bound.map(jobs, order_outputs=True)):
        results.append(r)
        if r.get("no_orphan_any_width"):
            print(f"height {h}: NO ORPHAN AT ANY WIDTH — certificate of {r['certificate_size']} states, "
                  f"verified={r['certificate_verified']} (stabilised at iteration {r['stabilised_at']})",
                  flush=True)
        elif r.get("proved_no_orphan_up_to") is not None:
            print(f"height {h} (k={r['k']}): PROVED no orphan of width <= {r['proved_no_orphan_up_to']}",
                  flush=True)
        else:
            print(f"height {h}: inconclusive after {r['max_iter']} iterations", flush=True)
    out = BUILD / f"modal-goe-lower-bounds-k{k}{'-mirror' if mirror else ''}.json"
    out.write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(f"DONE lower bounds -> {out}", flush=True)
