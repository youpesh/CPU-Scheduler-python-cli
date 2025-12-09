from __future__ import annotations

from typing import List, Optional

from .models import Process, ProcessMetrics, ScheduleResult, ScheduledSlice
from .metrics import compute_system_metrics


def schedule_fcfs(processes: List[Process], quantum: Optional[int] = None) -> ScheduleResult:
    """
    First-Come First-Serve (non-preemptive) scheduling.
    """
    processes_sorted = sorted(processes, key=lambda p: p.arrival_time)

    time = 0
    timeline: List[ScheduledSlice] = []
    metrics: List[ProcessMetrics] = []

    for p in processes_sorted:
        if time < p.arrival_time:
            time = p.arrival_time

        start_time = time
        end_time = start_time + p.burst_time

        timeline.append(ScheduledSlice(pid=p.pid, start_time=start_time, end_time=end_time))

        completion_time = end_time
        turnaround_time = completion_time - p.arrival_time
        waiting_time = start_time - p.arrival_time
        response_time = waiting_time  # first response equals waiting in FCFS

        metrics.append(
            ProcessMetrics(
                pid=p.pid,
                arrival_time=p.arrival_time,
                burst_time=p.burst_time,
                start_time=start_time,
                completion_time=completion_time,
                waiting_time=waiting_time,
                turnaround_time=turnaround_time,
                response_time=response_time,
                priority=p.priority,
            )
        )

        time = end_time

    result = ScheduleResult(algorithm="FCFS", quantum=quantum, processes=metrics, timeline=timeline)
    compute_system_metrics(result)
    return result


def schedule_sjf(processes: List[Process], quantum: Optional[int] = None) -> ScheduleResult:
    """
    Shortest Job First (non-preemptive).

    At each decision point, among processes that have arrived and are not yet
    completed, choose the one with the smallest burst time.
    """
    # Work on a shallow copy so we don't surprise callers.
    remaining: List[Process] = list(processes)

    time = 0
    timeline: List[ScheduledSlice] = []
    metrics: List[ProcessMetrics] = []
    completed_pids: set[str] = set()

    while len(completed_pids) < len(remaining):
        # Ready queue: processes that have arrived and are not completed.
        ready = [p for p in remaining if p.arrival_time <= time and p.pid not in completed_pids]

        if not ready:
            # If nothing is ready, jump time to the next arrival.
            next_arrival = min(p.arrival_time for p in remaining if p.pid not in completed_pids)
            time = next_arrival
            continue

        # Choose process with smallest burst time (tie-breaker: earlier arrival, then PID).
        p = min(
            ready,
            key=lambda x: (x.burst_time, x.arrival_time, x.pid),
        )

        start_time = time
        end_time = start_time + p.burst_time

        timeline.append(ScheduledSlice(pid=p.pid, start_time=start_time, end_time=end_time))

        completion_time = end_time
        turnaround_time = completion_time - p.arrival_time
        waiting_time = start_time - p.arrival_time
        response_time = waiting_time  # first run only; non-preemptive

        metrics.append(
            ProcessMetrics(
                pid=p.pid,
                arrival_time=p.arrival_time,
                burst_time=p.burst_time,
                start_time=start_time,
                completion_time=completion_time,
                waiting_time=waiting_time,
                turnaround_time=turnaround_time,
                response_time=response_time,
                priority=p.priority,
            )
        )

        completed_pids.add(p.pid)
        time = end_time

    result = ScheduleResult(algorithm="SJF (non-preemptive)", quantum=quantum, processes=metrics, timeline=timeline)
    compute_system_metrics(result)
    return result


def schedule_rr(processes: List[Process], quantum: Optional[int] = None) -> ScheduleResult:
    """
    Round Robin scheduling with a fixed time quantum.
    """
    if quantum is None or quantum <= 0:
        raise ValueError("Round Robin requires a positive quantum (use --quantum)")

    # Remaining burst time per PID
    remaining = {p.pid: p.burst_time for p in processes}
    proc_by_pid = {p.pid: p for p in processes}

    time = 0
    timeline: List[ScheduledSlice] = []
    metrics_map: dict[str, ProcessMetrics] = {}

    # Ready queue as list of PIDs
    ready: List[str] = []

    # Convenience: function to enqueue any newly arrived processes
    def enqueue_new_arrivals(current_time: int) -> None:
        for p in processes:
            if p.arrival_time <= current_time and p.pid not in ready and remaining[p.pid] > 0:
                # Only enqueue if not already present and still has remaining time
                ready.append(p.pid)

    # Initialize with processes that arrive at time 0
    enqueue_new_arrivals(time)

    while any(rt > 0 for rt in remaining.values()):
        if not ready:
            # Jump to next arrival if CPU is idle
            future_arrivals = [p.arrival_time for p in processes if remaining[p.pid] > 0 and p.arrival_time > time]
            if not future_arrivals:
                break
            time = min(future_arrivals)
            enqueue_new_arrivals(time)
            continue

        pid = ready.pop(0)
        p = proc_by_pid[pid]

        # If this is the first time the process runs, record its start/response
        if pid not in metrics_map:
            start_time = max(time, p.arrival_time)
            waiting_time = start_time - p.arrival_time
            metrics_map[pid] = ProcessMetrics(
                pid=pid,
                arrival_time=p.arrival_time,
                burst_time=p.burst_time,
                start_time=start_time,
                completion_time=0,  # filled later
                waiting_time=waiting_time,  # will be updated as total wait
                turnaround_time=0,  # filled later
                response_time=waiting_time,
                priority=p.priority,
            )
            if start_time > time:
                time = start_time

        run_time = min(quantum, remaining[pid])
        slice_start = time
        slice_end = time + run_time
        timeline.append(ScheduledSlice(pid=pid, start_time=slice_start, end_time=slice_end))

        time = slice_end
        remaining[pid] -= run_time

        # Enqueue any new arrivals that appeared during this slice
        enqueue_new_arrivals(time)

        if remaining[pid] > 0:
            # Put the process back at the end of the queue
            if pid not in ready:
                ready.append(pid)
        else:
            # Process finished; finalize its metrics
            m = metrics_map[pid]
            completion_time = time
            turnaround_time = completion_time - p.arrival_time
            # Total waiting = turnaround - burst
            waiting_time_total = turnaround_time - p.burst_time
            m.completion_time = completion_time
            m.turnaround_time = turnaround_time
            m.waiting_time = waiting_time_total

    metrics = list(metrics_map.values())
    result = ScheduleResult(algorithm="Round Robin", quantum=quantum, processes=metrics, timeline=timeline)
    compute_system_metrics(result)
    return result


def schedule_priority(processes: List[Process], quantum: Optional[int] = None) -> ScheduleResult:
    """
    Static Priority scheduling (non-preemptive).

    Lower numeric priority value means higher priority. Among ready
    processes, choose the one with the smallest priority; break ties
    by earlier arrival time, then PID.
    """
    remaining: List[Process] = list(processes)

    time = 0
    timeline: List[ScheduledSlice] = []
    metrics: List[ProcessMetrics] = []
    completed_pids: set[str] = set()

    while len(completed_pids) < len(remaining):
        ready = [
            p
            for p in remaining
            if p.arrival_time <= time and p.pid not in completed_pids
        ]

        if not ready:
            next_arrival = min(p.arrival_time for p in remaining if p.pid not in completed_pids)
            time = next_arrival
            continue

        def priority_key(p: Process):
            # Treat missing priority as lowest priority.
            prio = p.priority if p.priority is not None else float("inf")
            return (prio, p.arrival_time, p.pid)

        p = min(ready, key=priority_key)

        start_time = time
        end_time = start_time + p.burst_time

        timeline.append(ScheduledSlice(pid=p.pid, start_time=start_time, end_time=end_time))

        completion_time = end_time
        turnaround_time = completion_time - p.arrival_time
        waiting_time = start_time - p.arrival_time
        response_time = waiting_time

        metrics.append(
            ProcessMetrics(
                pid=p.pid,
                arrival_time=p.arrival_time,
                burst_time=p.burst_time,
                start_time=start_time,
                completion_time=completion_time,
                waiting_time=waiting_time,
                turnaround_time=turnaround_time,
                response_time=response_time,
                priority=p.priority,
            )
        )

        completed_pids.add(p.pid)
        time = end_time

    result = ScheduleResult(algorithm="Priority (static)", quantum=quantum, processes=metrics, timeline=timeline)
    compute_system_metrics(result)
    return result


def schedule_srtf(processes: List[Process], quantum: Optional[int] = None) -> ScheduleResult:
    """
    Shortest Remaining Time First (preemptive SJF).
    """
    remaining = {p.pid: p.burst_time for p in processes}
    proc_by_pid = {p.pid: p for p in processes}

    time = 0
    timeline: List[ScheduledSlice] = []
    metrics_map: dict[str, ProcessMetrics] = {}

    def next_arrival_after(t: int) -> Optional[int]:
        future = [p.arrival_time for p in processes if p.arrival_time > t and remaining[p.pid] > 0]
        return min(future) if future else None

    while any(rt > 0 for rt in remaining.values()):
        ready = [p for p in processes if p.arrival_time <= time and remaining[p.pid] > 0]
        if not ready:
            nxt = next_arrival_after(time)
            if nxt is None:
                break
            time = nxt
            continue

        # Choose process with smallest remaining time (tie: earlier arrival, then PID).
        current = min(ready, key=lambda p: (remaining[p.pid], p.arrival_time, p.pid))

        if current.pid not in metrics_map:
            start_time = max(time, current.arrival_time)
            response_time = start_time - current.arrival_time
            metrics_map[current.pid] = ProcessMetrics(
                pid=current.pid,
                arrival_time=current.arrival_time,
                burst_time=current.burst_time,
                start_time=start_time,
                completion_time=0,
                waiting_time=0,  # finalize later
                turnaround_time=0,
                response_time=response_time,
                priority=current.priority,
            )
            if start_time > time:
                time = start_time

        # Run until completion or next arrival, whichever comes first.
        nxt_arrival = next_arrival_after(time)
        if nxt_arrival is None:
            run_time = remaining[current.pid]
        else:
            run_time = min(remaining[current.pid], nxt_arrival - time)

        slice_start = time
        slice_end = time + run_time
        if run_time > 0:
            timeline.append(ScheduledSlice(pid=current.pid, start_time=slice_start, end_time=slice_end))

        time = slice_end
        remaining[current.pid] -= run_time

        if remaining[current.pid] == 0:
            completion_time = time
            turnaround_time = completion_time - current.arrival_time
            waiting_time = turnaround_time - current.burst_time

            m = metrics_map[current.pid]
            m.completion_time = completion_time
            m.turnaround_time = turnaround_time
            m.waiting_time = waiting_time

    metrics = list(metrics_map.values())
    result = ScheduleResult(algorithm="SRTF", quantum=quantum, processes=metrics, timeline=timeline)
    compute_system_metrics(result)
    return result


def schedule_mlfq(processes: List[Process], quantum: Optional[int] = None) -> ScheduleResult:
    """
    Multi-Level Feedback Queue with 3 levels and increasing quanta.

    - New arrivals enter the highest-priority queue (Q0).
    - Each queue uses round-robin with its quantum.
    - If a process uses its entire quantum and is not finished, it is demoted
      to the next lower queue (up to Q2).
    - If the CPU is idle, time jumps to the next arrival.
    """
    base_q = quantum if quantum and quantum > 0 else 2
    quanta = [base_q, base_q * 2, base_q * 4]

    remaining = {p.pid: p.burst_time for p in processes}
    proc_by_pid = {p.pid: p for p in processes}

    queues: List[List[str]] = [[], [], []]  # Q0, Q1, Q2
    metrics_map: dict[str, ProcessMetrics] = {}
    timeline: List[ScheduledSlice] = []

    time = 0

    def enqueue_new_arrivals(current_time: int) -> None:
        for p in processes:
            if p.arrival_time <= current_time and remaining[p.pid] > 0 and p.pid not in queues[0] and p.pid not in queues[1] and p.pid not in queues[2]:
                queues[0].append(p.pid)

    def any_ready() -> bool:
        return any(queues)

    def next_arrival_after(t: int) -> Optional[int]:
        future = [p.arrival_time for p in processes if p.arrival_time > t and remaining[p.pid] > 0]
        return min(future) if future else None

    enqueue_new_arrivals(time)

    while any(rt > 0 for rt in remaining.values()):
        if not any_ready():
            nxt = next_arrival_after(time)
            if nxt is None:
                break
            time = nxt
            enqueue_new_arrivals(time)
            continue

        # Pick highest-priority non-empty queue
        level = 0 if queues[0] else 1 if queues[1] else 2
        pid = queues[level].pop(0)
        p = proc_by_pid[pid]

        # First response
        if pid not in metrics_map:
            start_time = max(time, p.arrival_time)
            response_time = start_time - p.arrival_time
            metrics_map[pid] = ProcessMetrics(
                pid=pid,
                arrival_time=p.arrival_time,
                burst_time=p.burst_time,
                start_time=start_time,
                completion_time=0,
                waiting_time=0,  # finalize later
                turnaround_time=0,
                response_time=response_time,
                priority=p.priority,
            )
            if start_time > time:
                time = start_time

        run_time = min(quanta[level], remaining[pid])
        slice_start = time
        slice_end = time + run_time
        timeline.append(ScheduledSlice(pid=pid, start_time=slice_start, end_time=slice_end))

        time = slice_end
        remaining[pid] -= run_time

        enqueue_new_arrivals(time)

        if remaining[pid] > 0:
            # Demote if not already in lowest queue
            next_level = min(level + 1, 2)
            queues[next_level].append(pid)
        else:
            completion_time = time
            turnaround_time = completion_time - p.arrival_time
            waiting_time = turnaround_time - p.burst_time

            m = metrics_map[pid]
            m.completion_time = completion_time
            m.turnaround_time = turnaround_time
            m.waiting_time = waiting_time

    metrics = list(metrics_map.values())
    result = ScheduleResult(algorithm="MLFQ", quantum=base_q, processes=metrics, timeline=timeline)
    compute_system_metrics(result)
    return result


ALGORITHMS = {
    "fcfs": schedule_fcfs,
    "sjf": schedule_sjf,
    "rr": schedule_rr,
    "priority": schedule_priority,
    "srtf": schedule_srtf,
    "mlfq": schedule_mlfq,
}


def run_algorithm(name: str, processes: List[Process], quantum: Optional[int] = None) -> ScheduleResult:
    """
    Dispatch to the requested algorithm. Quantum is currently unused except
    for round-robin/MLFQ (to be implemented).
    """
    name = name.lower()
    if name not in ALGORITHMS:
        raise ValueError(f"Unknown or unimplemented algorithm '{name}'")

    func = ALGORITHMS[name]
    return func(processes, quantum=quantum)


