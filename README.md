## CPU Scheduling Simulator CLI

Fast start:
```bash
cd python-cli
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m scheduler_cli menu
```

Menu: pick algorithm by number; choose a workload from `examples/` or enter a path; quantum asked only for rr/mlfq.

Other common commands:
```bash
python -m scheduler_cli run --algorithm fcfs --workload examples/workload_small.json
python -m scheduler_cli compare --workload examples/workload_small.json --quantum 2
python -m scheduler_cli run --algorithm priority --workload examples/runway_workload.json
python -m scheduler_cli compare --workload examples/runway_workload.json --quantum 2
pytest
```

Workload format (JSON):
```json
[
  { "pid": "P1", "arrival_time": 0, "burst_time": 5, "priority": 2 }
]
```

CSV (header required):
```text
pid,arrival_time,burst_time,priority
P1,0,5,2
```

Notes: see `notes/runway.md` for the runway scenario; tests live in `tests/`.


