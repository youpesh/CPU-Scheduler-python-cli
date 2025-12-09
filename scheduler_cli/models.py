from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Process:
    pid: str
    arrival_time: int
    burst_time: int
    priority: Optional[int] = None


@dataclass
class ScheduledSlice:
    """
    One contiguous slice of execution for a process in the Gantt chart.
    """

    pid: str
    start_time: int
    end_time: int


@dataclass
class ProcessMetrics:
    pid: str
    arrival_time: int
    burst_time: int
    start_time: int
    completion_time: int
    waiting_time: int
    turnaround_time: int
    response_time: int
    priority: Optional[int] = None


@dataclass
class SystemMetrics:
    cpu_busy_time: int
    makespan: int
    throughput: float
    cpu_utilization: float
    starvation_count: int = 0


@dataclass
class ScheduleResult:
    algorithm: str
    quantum: Optional[int]
    processes: List[ProcessMetrics] = field(default_factory=list)
    timeline: List[ScheduledSlice] = field(default_factory=list)
    system: Optional[SystemMetrics] = None


