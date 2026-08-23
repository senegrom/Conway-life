#!/usr/bin/env python3
"""Summarise raw benchmark JSON into CSV and Markdown tables."""

from __future__ import annotations

from collections import defaultdict
import csv
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "benchmarks/results"


def main() -> int:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for path in sorted(RESULTS.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        groups[(data["workload_id"], data["engine_id"])].append(data)

    rows: list[dict[str, object]] = []
    for (workload, engine), runs in sorted(groups.items()):
        successful = [run for run in runs if run["return_code"] == 0]
        times = [float(run["wall_seconds"]) for run in successful]
        rss = [run.get("peak_rss_bytes") for run in successful if run.get("peak_rss_bytes") is not None]
        rows.append({
            "workload_id": workload,
            "engine_id": engine,
            "runs": len(runs),
            "successful": len(successful),
            "median_wall_seconds": statistics.median(times) if times else None,
            "min_wall_seconds": min(times) if times else None,
            "max_wall_seconds": max(times) if times else None,
            "median_peak_rss_bytes": int(statistics.median(rss)) if rss else None,
        })

    csv_path = ROOT / "benchmarks/summary.csv"
    fieldnames = [
        "workload_id", "engine_id", "runs", "successful", "median_wall_seconds",
        "min_wall_seconds", "max_wall_seconds", "median_peak_rss_bytes",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    def fmt(value: object) -> str:
        if value is None:
            return ""
        return f"{value:.6f}" if isinstance(value, float) else str(value)

    lines = [
        "# Benchmark summary", "",
        "Generated from raw JSON. Workload families must be interpreted separately.", "",
        "| Workload | Engine | Runs | OK | Median s | Min s | Max s | Median RSS bytes |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['workload_id']} | {row['engine_id']} | {row['runs']} | "
            f"{row['successful']} | {fmt(row['median_wall_seconds'])} | "
            f"{fmt(row['min_wall_seconds'])} | {fmt(row['max_wall_seconds'])} | "
            f"{fmt(row['median_peak_rss_bytes'])} |"
        )
    if not rows:
        lines.append("| _no results yet_ | | | | | | | |")
    (ROOT / "benchmarks/summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {csv_path} and benchmarks/summary.md from {sum(len(v) for v in groups.values())} runs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
