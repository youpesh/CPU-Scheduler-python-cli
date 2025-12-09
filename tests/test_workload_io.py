from pathlib import Path

from scheduler_cli.workload_io import load_workload
from scheduler_cli.models import Process


def test_load_json(tmp_path: Path):
    data = [
        {"pid": "A", "arrival_time": 0, "burst_time": 3, "priority": 1},
        {"pid": "B", "arrival_time": 1, "burst_time": 2},
    ]
    p = tmp_path / "w.json"
    p.write_text('[{"pid":"A","arrival_time":0,"burst_time":3,"priority":1},'
                 '{"pid":"B","arrival_time":1,"burst_time":2}]')
    procs = load_workload(p)
    assert isinstance(procs[0], Process)
    assert procs[1].priority is None
    assert procs[1].arrival_time == 1


def test_load_csv(tmp_path: Path):
    p = tmp_path / "w.csv"
    p.write_text("pid,arrival_time,burst_time,priority\nA,0,3,1\nB,1,2,\n")
    procs = load_workload(p)
    assert procs[0].pid == "A"
    assert procs[1].priority is None


