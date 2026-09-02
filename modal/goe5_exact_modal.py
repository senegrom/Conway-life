"""Modal runner for scripts/goe5_exact.py (exact width bounds, streamed).

    modal run modal/goe5_exact_modal.py --height 5 --mirror 1 --max-depth 46
    modal run modal/goe5_exact_modal.py --height 4 --max-depth 12      # sanity: no orphans (Wade)
"""

from __future__ import annotations

import json
from pathlib import Path

import modal

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
BUILD = Path(r"D:\Programs\life-research\build")

app = modal.App("conway-goe5-exact")
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("python-sat", "numpy")
    .add_local_dir(str(SCRIPTS), remote_path="/root/scripts")
)


@app.function(image=image, cpu=8.0, memory=64 * 1024, timeout=12 * 3600)
def run(height: int, max_depth: int, cap: int, mirror: bool, antichain: bool, filter_cap: int) -> dict:
    import sys
    sys.path.insert(0, "/root/scripts")
    from goe5_exact import bfs
    return bfs(height, max_depth, cap, mirror, log=lambda s: print(s, flush=True),
               antichain=antichain, filter_cap=filter_cap)


@app.local_entrypoint()
def main(height: int = 5, max_depth: int = 46, cap: int = 200000, mirror: int = 0,
         antichain: int = 1, filter_cap: int = 40000):
    r = run.remote(height, max_depth, cap, bool(mirror), bool(antichain), filter_cap)
    print(r, flush=True)
    tag = f"h{height}{'-mirror' if mirror else ''}"
    (BUILD / f"modal-goe-exact-{tag}.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    if r.get("orphan_width"):
        print(f"*** NARROWEST ORPHAN height {height}{' (mirror-symmetric columns)' if mirror else ''}: "
              f"width {r['orphan_width']}", flush=True)
    else:
        print(f"PROVED: no orphan of height {height}{' with mirror-symmetric columns' if mirror else ''} "
              f"has width <= {r['proved_no_orphan_up_to']} ({r['stopped']}, frontier {r['frontier']})", flush=True)
