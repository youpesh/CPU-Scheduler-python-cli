from scheduler_cli.algorithms import (
    schedule_fcfs,
    schedule_sjf,
    schedule_rr,
    schedule_priority,
    schedule_srtf,
    schedule_mlfq,
)
from scheduler_cli.models import Process


def _procs():
    return [
        Process("P1", arrival_time=0, burst_time=5, priority=2),
        Process("P2", arrival_time=1, burst_time=3, priority=1),
        Process("P3", arrival_time=2, burst_time=8, priority=3),
    ]


def test_fcfs_order():
    res = schedule_fcfs(_procs())
    assert [s.pid for s in res.timeline] == ["P1", "P2", "P3"]
    assert res.processes[0].waiting_time == 0
    assert res.processes[1].waiting_time == 4
    assert res.processes[2].waiting_time == 6


def test_sjf_order():
    res = schedule_sjf(_procs())
    assert [s.pid for s in res.timeline] == ["P1", "P2", "P3"]
    # Same order here because P1 arrives first and is shortest among ready at t=0, then P2 < P3


def test_rr_quantum_2():
    res = schedule_rr(_procs(), quantum=2)
    # Ensure all processes appear in timeline and total time matches sum of bursts
    assert {s.pid for s in res.timeline} == {"P1", "P2", "P3"}
    assert sum(p.burst_time for p in _procs()) == res.system.cpu_busy_time


def test_priority_static():
    res = schedule_priority(_procs())
    # P2 has highest priority (1), should run first when all ready by time 2
    assert res.timeline[0].pid in {"P1"}  # P1 starts at 0
    assert res.timeline[1].pid == "P2"


def test_srtf_completes():
    res = schedule_srtf(_procs())
    assert {p.pid for p in res.processes} == {"P1", "P2", "P3"}
    assert res.system.cpu_busy_time == sum(p.burst_time for p in _procs())


def test_mlfq_completes():
    res = schedule_mlfq(_procs(), quantum=2)
    assert {p.pid for p in res.processes} == {"P1", "P2", "P3"}
    assert res.system.cpu_busy_time == sum(p.burst_time for p in _procs())


