from __future__ import annotations

from typing import List

from .models import ProcessMetrics, ScheduleResult, SystemMetrics


def compute_system_metrics(result: ScheduleResult) -> SystemMetrics:
    """
    Compute throughput and CPU utilization given populated per-process metrics
    and timeline slices.
    """
    if not result.processes:
        return SystemMetrics(cpu_busy_time=0, makespan=0, throughput=0.0, cpu_utilization=0.0)

    makespan = max(p.completion_time for p in result.processes)
    cpu_busy_time = sum(slice_.end_time - slice_.start_time for slice_ in result.timeline)

    throughput = len(result.processes) / makespan if makespan > 0 else 0.0
    cpu_utilization = cpu_busy_time / makespan if makespan > 0 else 0.0

    # Starvation detection is algorithm-specific; for now, count processes whose
    # waiting time is more than 2x the average waiting time.
    avg_wait = sum(p.waiting_time for p in result.processes) / len(result.processes)
    starvation_count = sum(1 for p in result.processes if p.waiting_time > 2 * avg_wait)

    system = SystemMetrics(
        cpu_busy_time=cpu_busy_time,
        makespan=makespan,
        throughput=throughput,
        cpu_utilization=cpu_utilization,
        starvation_count=starvation_count,
    )
    result.system = system
    return system


def summarize_process_metrics(processes: List[ProcessMetrics]) -> dict:
    """
    Return averages of the key per-process metrics for quick comparison.
    """
    if not processes:
        return {"avg_waiting": 0.0, "avg_turnaround": 0.0, "avg_response": 0.0}

    n = len(processes)
    return {
        "avg_waiting": sum(p.waiting_time for p in processes) / n,
        "avg_turnaround": sum(p.turnaround_time for p in processes) / n,
        "avg_response": sum(p.response_time for p in processes) / n,
    }


