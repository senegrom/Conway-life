#!/usr/bin/env python3
"""f >= 2 hunt in the asymmetric flip neighbourhood of known ringed orphans.

Takes the census of dead-ringed orphans (data/discoveries/
d4-ring-orphans-11x11.txt) and enumerates all variants of each member with
--depth cells flipped (depth 1 = 121 singles, depth 2 = 7,260 doubles per
member). These variants sit next to deep orphan territory but are
asymmetric, so no symmetric census can see them. Per variant (fast
incremental templates, pad^2 checked first as the common exit):

    pad^2 SAT               -> not interesting, skip
    pad^2 UNSAT, pad^1 SAT  -> F2-WITNESS: f = 2, improves the Salo-Torma
                               padding-constant lower bound to 2
    pad^1 UNSAT, bare SAT   -> F1: another f = 1 witness (asymmetric)
    both UNSAT              -> F0: an asymmetric dead-ringed orphan

F2 finds are always re-verified with the slow exhaustively validated
checker; F1 finds are slow-verified up to a cap. Member ranges allow
parallel workers.
"""

from __future__ import annotations

import argparse
import itertools
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preimage_sat as ps
from padding_flip import pad_window
from ring_orphan_search import WindowTemplate

ENTRY_RE = re.compile(
    r"# (F1-WITNESS|DEAD-RINGED-ORPHAN) (\d+)x\2 (\w+) population (\d+) "
    r"\(orbit-code (\d+)\)\n((?:[01]+\n)+)"
)


def load_census(path: Path) -> list[tuple[str, list[list[int]]]]:
    entries = []
    for m in ENTRY_RE.finditer(path.read_text(encoding="utf-8")):
        raster = [[int(c) for c in line] for line in m.group(6).strip().splitlines()]
        entries.append((m.group(5), raster))
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--census", type=Path,
                        default=Path(__file__).resolve().parent.parent
                        / "data" / "discoveries" / "d4-ring-orphans-11x11.txt")
    parser.add_argument("--depth", type=int, choices=[1, 2], required=True)
    parser.add_argument("--start", type=int, default=0, help="member index")
    parser.add_argument("--end", type=int, help="member index, exclusive")
    parser.add_argument("--report-every", type=float, default=300.0)
    parser.add_argument("--slow-verify-f1", type=int, default=20)
    args = parser.parse_args()

    entries = load_census(args.census)
    end = args.end if args.end is not None else len(entries)
    k = len(entries[0][1])
    print(f"flip search: {len(entries)} census members, k={k}, "
          f"depth {args.depth}, members [{args.start}, {end})", flush=True)

    ring2 = WindowTemplate(k + 4, k + 4, 2)
    ring1 = WindowTemplate(k + 2, k + 2, 1)
    bare = WindowTemplate(k, k, 0)
    cells = [(i, j) for i in range(k) for j in range(k)]
    pos_of = {c: p for p, c in enumerate(cells)}
    r2v = [ring2.w_var[(i + 2, j + 2)] for i, j in cells]
    r1v = [ring1.w_var[(i + 1, j + 1)] for i, j in cells]
    bv = [bare.w_var[(i, j)] for i, j in cells]

    t0 = time.perf_counter()
    last = t0
    counts = {0: 0, 1: 0, 2: 0}
    f1_slow_left = args.slow_verify_f1
    checked = 0
    total = (end - args.start) * (
        len(cells) if args.depth == 1
        else len(cells) * (len(cells) - 1) // 2
    )
    for mi in range(args.start, end):
        code, raster = entries[mi]
        base_bits = [raster[i][j] for i, j in cells]
        base2 = [v if b else -v for v, b in zip(r2v, base_bits)]
        base1 = [v if b else -v for v, b in zip(r1v, base_bits)]
        baseb = [v if b else -v for v, b in zip(bv, base_bits)]
        for flips in itertools.combinations(cells, args.depth):
            checked += 1
            a2 = list(base2)
            for c in flips:
                a2[pos_of[c]] = -a2[pos_of[c]]
            if ring2.has_preimage(a2):
                now = time.perf_counter()
                if now - last > args.report_every:
                    print(f"  {checked}/{total}, {checked / (now - t0):.0f}/s, "
                          f"f0={counts[0]} f1={counts[1]} f2={counts[2]}",
                          flush=True)
                    last = now
                continue
            a1 = list(base1)
            ab = list(baseb)
            for c in flips:
                a1[pos_of[c]] = -a1[pos_of[c]]
                ab[pos_of[c]] = -ab[pos_of[c]]
            variant = [row[:] for row in raster]
            for i, j in flips:
                variant[i][j] ^= 1
            pop = sum(map(sum, variant))
            flips_s = ";".join(f"{i},{j}" for i, j in flips)

            if ring1.has_preimage(a1):
                slow1, _ = ps.check_window(pad_window(variant, 1))
                slow2, _ = ps.check_window(pad_window(variant, 2))
                if slow1 and not slow2:
                    counts[2] += 1
                    print(f"*** F2-WITNESS (slow-verified) member={code} "
                          f"flips={flips_s} pop={pop} — PADDING CONSTANT >= 2",
                          flush=True)
                else:
                    print(f"MISMATCH f2-candidate member={code} flips={flips_s}: "
                          f"slow pad1={slow1} pad2={slow2} — investigate!",
                          flush=True)
                for row in variant:
                    print("".join(map(str, row)), flush=True)
            elif bare.has_preimage(ab):
                counts[1] += 1
                if f1_slow_left > 0:
                    f1_slow_left -= 1
                    slow0, _ = ps.check_window(variant)
                    slow1, _ = ps.check_window(pad_window(variant, 1))
                    tag = (" (slow-verified)" if slow0 and not slow1
                           else " SLOW MISMATCH — investigate!")
                    print(f"F1-WITNESS{tag} member={code} flips={flips_s} "
                          f"pop={pop}", flush=True)
                    for row in variant:
                        print("".join(map(str, row)), flush=True)
                else:
                    print(f"F1 member={code} flips={flips_s} pop={pop}",
                          flush=True)
            else:
                counts[0] += 1
                print(f"F0 member={code} flips={flips_s} pop={pop}", flush=True)

    print(f"DONE flips depth={args.depth} members [{args.start},{end}): "
          f"f0={counts[0]} f1={counts[1]} f2={counts[2]}, "
          f"{time.perf_counter() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
