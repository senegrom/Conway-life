#!/usr/bin/env python3
"""Run a benchmark command and save a reproducible JSON record."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import uuid

try:
    import resource
except ImportError:  # pragma: no cover - native Windows only
    resource = None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path | None) -> str | None:
    if path is None or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def child_peak_rss_bytes() -> int | None:
    if resource is None:
        return None
    value = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    # Linux reports KiB; macOS reports bytes.
    return int(value if sys.platform == "darwin" else value * 1024)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-id", required=True)
    parser.add_argument("--engine-version")
    parser.add_argument("--engine-commit")
    parser.add_argument("--algorithm")
    parser.add_argument("--workload-id", required=True)
    parser.add_argument("--input-file", type=Path)
    parser.add_argument("--state-file", type=Path)
    parser.add_argument("--topology")
    parser.add_argument("--generations", type=int, required=True)
    parser.add_argument("--repetition", type=int, default=1)
    parser.add_argument("--cold-start", action="store_true")
    parser.add_argument("--gpu")
    parser.add_argument("--driver")
    parser.add_argument("--compiler")
    parser.add_argument("--build-flags")
    parser.add_argument("--notes")
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("a command is required after --")
    if args.generations < 0:
        parser.error("--generations must be non-negative")
    if args.repetition < 1:
        parser.error("--repetition must be at least 1")

    started = datetime.now(timezone.utc)
    start = time.perf_counter()
    completed = subprocess.run(command, capture_output=True, check=False)
    wall = time.perf_counter() - start
    peak_rss = child_peak_rss_bytes()

    result_path = args.result
    result_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path = result_path.with_suffix(result_path.suffix + ".stdout.txt")
    stderr_path = result_path.with_suffix(result_path.suffix + ".stderr.txt")
    stdout_path.write_bytes(completed.stdout)
    stderr_path.write_bytes(completed.stderr)

    record = {
        "schema_version": "1.0",
        "run_id": str(uuid.uuid4()),
        "timestamp_utc": started.isoformat().replace("+00:00", "Z"),
        "engine_id": args.engine_id,
        "engine_version": args.engine_version,
        "engine_commit": args.engine_commit,
        "algorithm": args.algorithm,
        "workload_id": args.workload_id,
        "input_sha256": sha256_file(args.input_file),
        "topology": args.topology,
        "generations": args.generations,
        "repetition": args.repetition,
        "cold_start": args.cold_start,
        "command": command,
        "wall_seconds": wall,
        "initialization_seconds": None,
        "update_seconds": None,
        "peak_rss_bytes": peak_rss,
        "peak_vram_bytes": None,
        "return_code": completed.returncode,
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "cpu": platform.processor() or None,
            "gpu": args.gpu,
            "ram_bytes": None,
            "driver": args.driver,
            "compiler": args.compiler,
            "build_flags": args.build_flags,
        },
        "output": {
            "state_file": str(args.state_file) if args.state_file else None,
            "sha256": sha256_file(args.state_file),
            "stdout_sha256": sha256_bytes(completed.stdout),
            "stderr_sha256": sha256_bytes(completed.stderr),
        },
        "logs": {
            "stdout_file": str(stdout_path),
            "stderr_file": str(stderr_path),
        },
        "notes": args.notes,
    }

    result_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {result_path}")
    print(f"Return code: {completed.returncode}; wall time: {wall:.6f} s")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
