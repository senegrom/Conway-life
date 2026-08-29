#!/usr/bin/env python3
"""f >= 2 hunt in the single-flip neighbourhoods of known f = 1 witnesses.

An f = 1 witness sits exactly on the pad^1 SAT/UNSAT boundary: bare
window preimageable, one dead ring an orphan (hence two rings an orphan
too, by anti-monotonicity). Flipping one cell can push pad^1 back to
SAT; if pad^2 stays UNSAT the variant has f = 2 — improving the known
lower bound of the Salo-Torma padding constant (Q28820954 / LIFE-F001).
No other sweep covers this territory: single flips of the double-flip
witnesses are TRIPLE flips of census members, and the 13x13 witnesses'
neighbourhoods are untouched.

Witness sources (harvested from campaign outputs at start-up):
  --size 11: the 1,080 double-flip witnesses from f2flips-d2-*.out
             (verified raster blocks + compact lines reconstructed via
             the census file). The 4 census and 60 single-flip
             witnesses are excluded — their single-flip neighbourhoods
             are subsets of the completed depth-1/2 census sweeps.
  --size 13: every F1-WITNESS block in f2deep13-*.out (snapshot; rerun
             after the deep campaign ends to cover late finds).

Each witness is re-checked (bare SAT, pad^1 UNSAT) before use. Per
variant: pad^1 first (UNSAT = common cheap exit), pad^2 only for
pad^1-SAT survivors; any pad^2-UNSAT candidate is re-verified with the
slow exhaustively validated checker before being reported.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preimage_sat as ps
from padding_flip import pad_window
from ring_orphan_search import WindowTemplate

BUILD = Path(r"D:\Programs\life-research\build")
CENSUS = Path(__file__).resolve().parent.parent / "data" / "discoveries" / "d4-ring-orphans-11x11.txt"


def _grid(text: str) -> list[list[int]]:
    return [[int(c) for c in row] for row in text.split()]


def harvest_witnesses(size: int) -> list[tuple[str, list[list[int]]]]:
    wit: dict[tuple, str] = {}
    if size == 11:
        census: dict[str, list[list[int]]] = {}
        text = CENSUS.read_text(encoding="utf-8")
        for m in re.finditer(
            r"# (?:F1-WITNESS|DEAD-RINGED-ORPHAN) 11x11 d4 population \d+ "
            r"\(orbit-code (\d+)\)\n((?:[01]{11}\n){11})", text
        ):
            census[m.group(1)] = _grid(m.group(2))
        for f in sorted(BUILD.glob("f2flips-d2-*.out")):
            t = f.read_text(encoding="utf-8")
            for m in re.finditer(
                r"F1-WITNESS \(slow-verified\) member=(\d+) flips=(\S+) "
                r"pop=\d+\n((?:[01]{11}\n){11})", t
            ):
                wit[tuple(map(tuple, _grid(m.group(3))))] = \
                    f"d2:{m.group(1)}:{m.group(2)}"
            for m in re.finditer(r"^F1 member=(\d+) flips=(\S+) pop=\d+$", t, re.M):
                base = census.get(m.group(1))
                if base is None:
                    continue
                raster = [row[:] for row in base]
                for fl in m.group(2).split(";"):
                    i, j = map(int, fl.split(","))
                    raster[i][j] ^= 1
                wit[tuple(map(tuple, raster))] = f"d2:{m.group(1)}:{m.group(2)}"
    else:
        for f in sorted(BUILD.glob("f2deep13-*.out")):
            t = f.read_text(encoding="utf-8")
            for m in re.finditer(
                r"F1-WITNESS \(slow-verified\) bits=(\d+) pop=\d+ core=13 "
                r"group=d4\n((?:[01]{13}\n){13})", t
            ):
                wit[tuple(map(tuple, _grid(m.group(2))))] = f"deep13:{m.group(1)}"
    return [(label, [list(r) for r in raster]) for raster, label in wit.items()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, choices=[11, 13], required=True)
    parser.add_argument("--start", type=int, default=0, help="witness index")
    parser.add_argument("--end", type=int, help="witness index, exclusive")
    parser.add_argument("--report-every", type=float, default=300.0)
    args = parser.parse_args()

    k = args.size
    wits = harvest_witnesses(k)
    end = args.end if args.end is not None else len(wits)
    print(f"witness-flip f2 search: {len(wits)} known f=1 witnesses of size "
          f"{k}, range [{args.start}, {end})", flush=True)

    ring1 = WindowTemplate(k + 2, k + 2, 1)
    ring2 = WindowTemplate(k + 4, k + 4, 2)
    bare = WindowTemplate(k, k, 0)
    cells = [(i, j) for i in range(k) for j in range(k)]
    r1v = [ring1.w_var[(i + 1, j + 1)] for i, j in cells]
    r2v = [ring2.w_var[(i + 2, j + 2)] for i, j in cells]
    bv = [bare.w_var[(i, j)] for i, j in cells]
    pos = {c: p for p, c in enumerate(cells)}

    t0 = time.perf_counter()
    last = t0
    checked = f2 = p1sat = bad = 0
    seen: set[tuple] = set()
    for wi in range(args.start, end):
        label, raster = wits[wi]
        bits = [raster[i][j] for i, j in cells]
        b1 = [v if b else -v for v, b in zip(r1v, bits)]
        b2 = [v if b else -v for v, b in zip(r2v, bits)]
        bb = [v if b else -v for v, b in zip(bv, bits)]
        if ring1.has_preimage(b1) or not bare.has_preimage(bb):
            print(f"  WARN: {label} failed f=1 re-check — skipped", flush=True)
            bad += 1
            continue
        for (i, j) in cells:
            now = time.perf_counter()
            if now - last > args.report_every:
                print(f"  wit {wi - args.start + 1}/{end - args.start}, "
                      f"{checked} variants, {checked / (now - t0):.0f}/s, "
                      f"pad1-SAT {p1sat}, f2 {f2}", flush=True)
                last = now
            variant = [row[:] for row in raster]
            variant[i][j] ^= 1
            key = tuple(map(tuple, variant))
            if key in seen:
                continue
            seen.add(key)
            checked += 1
            p = pos[(i, j)]
            a1 = b1[:]
            a1[p] = -a1[p]
            if not ring1.has_preimage(a1):
                continue  # pad^1 still an orphan: f <= 1 territory
            p1sat += 1
            a2 = b2[:]
            a2[p] = -a2[p]
            if ring2.has_preimage(a2):
                continue
            slow1, _ = ps.check_window(pad_window(variant, 1))
            slow2, _ = ps.check_window(pad_window(variant, 2))
            if slow1 and not slow2:
                f2 += 1
                print(f"*** F2-WITNESS (slow-verified) size={k} from={label} "
                      f"flip={i},{j} pop={sum(map(sum, variant))} — "
                      f"PADDING CONSTANT >= 2", flush=True)
            else:
                print(f"MISMATCH f2-candidate from={label} flip={i},{j}: "
                      f"slow pad1={slow1} pad2={slow2} — investigate!",
                      flush=True)
            for row in variant:
                print("".join(map(str, row)), flush=True)
    print(f"DONE wflip {k} [{args.start},{end}): witnesses "
          f"{end - args.start - bad}, variants {checked}, pad1-SAT {p1sat}, "
          f"f2={f2}, {time.perf_counter() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
