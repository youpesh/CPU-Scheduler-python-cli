from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, List

from .models import Process


def load_workload(path: str | Path) -> List[Process]:
    """
    Load a workload from a JSON or CSV file into a list of Process objects.
    """
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".json":
        return _load_json(path)
    if suffix == ".csv":
        return _load_csv(path)

    raise ValueError(f"Unsupported workload format: {suffix} (use .json or .csv)")


def _load_json(path: Path) -> List[Process]:
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, Iterable):
        raise ValueError("JSON workload must be a list of process objects")

    processes: List[Process] = []
    for entry in raw:
        processes.append(_process_from_mapping(entry))

    return processes


def _load_csv(path: Path) -> List[Process]:
    processes: List[Process] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            processes.append(_process_from_mapping(row))
    return processes


def _process_from_mapping(mapping) -> Process:
    try:
        pid = str(mapping["pid"])
        arrival_time = int(mapping["arrival_time"])
        burst_time = int(mapping["burst_time"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid process entry: {mapping!r}") from exc

    priority_val = mapping.get("priority")
    priority = int(priority_val) if priority_val not in (None, "") else None

    return Process(
        pid=pid,
        arrival_time=arrival_time,
        burst_time=burst_time,
        priority=priority,
    )


