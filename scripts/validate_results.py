#!/usr/bin/env python3
"""Validate registries, pinned patterns and benchmark result JSON."""

from __future__ import annotations

import csv
from datetime import date, datetime
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HEX64 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_RESULT_KEYS = {
    "schema_version", "run_id", "timestamp_utc", "engine_id", "workload_id",
    "generations", "command", "wall_seconds", "return_code", "host", "output",
}


class ValidationError(Exception):
    pass


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_csv_ids(path: Path, id_column: str) -> set[str]:
    rows = csv_rows(path)
    ids = [row.get(id_column, "") for row in rows]
    if any(not item for item in ids):
        raise ValidationError(f"{path}: empty {id_column}")
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in ids:
        if item in seen:
            duplicates.add(item)
        seen.add(item)
    if duplicates:
        raise ValidationError(f"{path}: duplicate IDs: {sorted(duplicates)}")
    return set(ids)


def validate_dates(path: Path, column: str) -> None:
    for line_no, row in enumerate(csv_rows(path), start=2):
        try:
            date.fromisoformat(row[column])
        except Exception as exc:
            raise ValidationError(f"{path}:{line_no}: invalid {column}: {row.get(column)!r}") from exc


def validate_urls(path: Path, column: str) -> None:
    for line_no, row in enumerate(csv_rows(path), start=2):
        value = row.get(column, "")
        if not value.startswith(("https://", "http://")):
            raise ValidationError(f"{path}:{line_no}: invalid URL in {column}: {value!r}")


def validate_hash(value: Any, field: str, path: Path, nullable: bool = True) -> None:
    if value is None and nullable:
        return
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise ValidationError(f"{path}: {field} must be null or lowercase SHA-256")


def validate_result(path: Path, engine_ids: set[str], workload_ids: set[str]) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValidationError(f"{path}: invalid JSON") from exc

    missing = REQUIRED_RESULT_KEYS - data.keys()
    if missing:
        raise ValidationError(f"{path}: missing keys {sorted(missing)}")
    if data["schema_version"] != "1.0":
        raise ValidationError(f"{path}: unsupported schema_version")
    if data["engine_id"] not in engine_ids:
        raise ValidationError(f"{path}: unknown engine_id {data['engine_id']!r}")
    if data["workload_id"] not in workload_ids:
        raise ValidationError(f"{path}: unknown workload_id {data['workload_id']!r}")
    if not isinstance(data["generations"], int) or data["generations"] < 0:
        raise ValidationError(f"{path}: generations must be a non-negative integer")
    if not isinstance(data["wall_seconds"], (int, float)) or data["wall_seconds"] < 0:
        raise ValidationError(f"{path}: wall_seconds must be non-negative")
    if not isinstance(data["command"], list) or not data["command"] or not all(isinstance(x, str) for x in data["command"]):
        raise ValidationError(f"{path}: command must be a nonempty list of strings")
    try:
        datetime.fromisoformat(data["timestamp_utc"].replace("Z", "+00:00"))
    except Exception as exc:
        raise ValidationError(f"{path}: invalid timestamp_utc") from exc

    validate_hash(data.get("input_sha256"), "input_sha256", path)
    output = data["output"]
    if not isinstance(output, dict):
        raise ValidationError(f"{path}: output must be an object")
    for key in ("sha256", "stdout_sha256", "stderr_sha256"):
        validate_hash(output.get(key), f"output.{key}", path, nullable=(key == "sha256"))


def load_reference_module():
    module_path = ROOT / "scripts/reference_life.py"
    spec = importlib.util.spec_from_file_location("reference_life", module_path)
    if spec is None or spec.loader is None:
        raise ValidationError("could not load reference_life.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_patterns() -> None:
    ref = load_reference_module()
    patterns = ROOT / "benchmarks/patterns"
    block = ref.read_rle(patterns / "block.rle").live
    blinker = ref.read_rle(patterns / "blinker.rle").live
    glider = ref.read_rle(patterns / "glider.rle").live
    if ref.advance(block, 1) != block:
        raise ValidationError("block.rle is not stable")
    if ref.advance(blinker, 2) != blinker:
        raise ValidationError("blinker.rle is not period 2")
    shifted = frozenset((x + 1, y + 1) for x, y in glider)
    if ref.advance(glider, 4) != shifted:
        raise ValidationError("glider.rle does not shift by (1,1) after four generations")


def main() -> int:
    try:
        source_ids = load_csv_ids(ROOT / "data/sources.csv", "source_id")
        engine_ids = load_csv_ids(ROOT / "data/engine-registry.csv", "engine_id")
        problem_ids = load_csv_ids(ROOT / "data/open-problems.csv", "problem_id")
        workload_ids = load_csv_ids(ROOT / "benchmarks/workloads.csv", "workload_id")
        validate_dates(ROOT / "data/sources.csv", "last_checked")
        validate_dates(ROOT / "data/open-problems.csv", "last_checked")
        validate_urls(ROOT / "data/sources.csv", "url")
        validate_urls(ROOT / "data/engine-registry.csv", "source")
        validate_urls(ROOT / "data/open-problems.csv", "primary_source")
        validate_patterns()
        result_paths = sorted((ROOT / "benchmarks/results").glob("*.json"))
        for path in result_paths:
            validate_result(path, engine_ids, workload_ids)
        print(
            f"Validated {len(source_ids)} sources, {len(engine_ids)} engines, "
            f"{len(problem_ids)} problems, {len(workload_ids)} workloads, "
            f"{len(result_paths)} result files."
        )
        return 0
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
