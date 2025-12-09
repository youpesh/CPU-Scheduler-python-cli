from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import List

from rich import box
from rich.console import Console
from rich.table import Table

from .algorithms import ALGORITHMS, run_algorithm
from .gantt import build_rich_gantt
from .metrics import summarize_process_metrics
from .models import ScheduleResult
from .workload_io import load_workload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scheduler-cli",
        description="CPU scheduling simulator (FCFS, SJF, RR, Priority, SRTF, MLFQ).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a scheduling algorithm on a workload file.")
    run_parser.add_argument(
        "--algorithm",
        "-a",
        required=True,
        help="Algorithm to use (fcfs, sjf, rr, priority, srtf, mlfq).",
    )
    run_parser.add_argument(
        "--workload",
        "-w",
        required=True,
        help="Path to JSON or CSV workload file.",
    )
    run_parser.add_argument(
        "--quantum",
        "-q",
        type=int,
        default=None,
        help="Time quantum for round-robin / MLFQ (ignored by FCFS, SJF, Priority).",
    )
    run_parser.add_argument(
        "--step",
        action="store_true",
        help="Show a simple time-stepped simulation in the terminal.",
    )
    run_parser.add_argument(
        "--step-delay",
        type=float,
        default=0.3,
        help="Seconds to wait between steps when --step is used (default: 0.3).",
    )

    compare_parser = subparsers.add_parser(
        "compare",
        help="Run multiple algorithms on the same workload and compare average metrics.",
    )
    compare_parser.add_argument(
        "--workload",
        "-w",
        required=True,
        help="Path to JSON or CSV workload file.",
    )
    compare_parser.add_argument(
        "--algorithms",
        "-a",
        nargs="+",
        default=["fcfs", "sjf", "rr", "priority", "srtf", "mlfq"],
        help="Algorithms to compare (default: fcfs sjf rr priority srtf mlfq).",
    )
    compare_parser.add_argument(
        "--quantum",
        "-q",
        type=int,
        default=2,
        help="Time quantum used for RR/MLFQ when included (default: 2).",
    )

    menu_parser = subparsers.add_parser(
        "menu",
        help="Interactive menu to pick an algorithm and workload at runtime.",
    )
    menu_parser.add_argument(
        "--workload",
        "-w",
        default="examples/workload_small.json",
        help="Default workload path to prefill in the menu (default: examples/workload_small.json).",
    )
    menu_parser.add_argument(
        "--quantum",
        "-q",
        type=int,
        default=2,
        help="Default quantum to prefill for RR/MLFQ (default: 2).",
    )

    return parser


def _print_result(result: ScheduleResult) -> None:
    console = Console()

    console.print(f"[bold]Algorithm:[/bold] {result.algorithm}")
    if result.quantum is not None:
        console.print(f"[bold]Quantum:[/bold] {result.quantum}")

    console.print()

    panel, time_marks = build_rich_gantt(result.timeline)
    console.print(panel)
    if time_marks:
        console.print(time_marks)

    console.print()

    headers = [
        "PID",
        "Arrive",
        "Burst",
        "Start",
        "Complete",
        "Wait",
        "Turnaround",
        "Response",
        "Priority",
    ]

    proc_table = Table(title="Per-process metrics", box=box.SIMPLE_HEAVY)
    for h in headers:
        justify = "center" if h in {"PID", "Priority"} else "right"
        proc_table.add_column(h, justify=justify)

    for p in result.processes:
        proc_table.add_row(
            p.pid,
            str(p.arrival_time),
            str(p.burst_time),
            str(p.start_time),
            str(p.completion_time),
            str(p.waiting_time),
            str(p.turnaround_time),
            str(p.response_time),
            "" if p.priority is None else str(p.priority),
        )

    console.print(proc_table)
    console.print()

    summary = summarize_process_metrics(result.processes)
    if result.system:
        sys = result.system
        sys_table = Table(title="System metrics", box=box.SIMPLE_HEAVY)
        sys_table.add_column("Metric")
        sys_table.add_column("Value", justify="right")

        sys_table.add_row("Avg waiting", f"{summary['avg_waiting']:.2f}")
        sys_table.add_row("Avg turnaround", f"{summary['avg_turnaround']:.2f}")
        sys_table.add_row("Avg response", f"{summary['avg_response']:.2f}")
        sys_table.add_row("Throughput (proc/time)", f"{sys.throughput:.3f}")
        sys_table.add_row("CPU utilization", f"{sys.cpu_utilization*100:.1f}%")
        sys_table.add_row("Starvation count", str(sys.starvation_count))

        console.print(sys_table)


def _run_compare(workload_path: Path, quantum: int, console: Console) -> None:
    """
    Run the standard compare set on a workload and print the summary table.
    """
    processes = load_workload(workload_path)
    algorithms = ["fcfs", "sjf", "rr", "priority", "srtf", "mlfq"]

    summary_table = Table(title=f"Algorithm comparison: {workload_path}", box=box.SIMPLE_HEAVY)
    summary_table.add_column("Algorithm")
    summary_table.add_column("Quantum", justify="right")
    summary_table.add_column("Avg waiting", justify="right")
    summary_table.add_column("Avg turnaround", justify="right")
    summary_table.add_column("Avg response", justify="right")

    for alg in algorithms:
        q = quantum if alg in {"rr", "mlfq"} else None
        result = run_algorithm(alg, list(processes), quantum=q)
        summary = summarize_process_metrics(result.processes)
        summary_table.add_row(
            result.algorithm,
            "" if result.quantum is None else str(result.quantum),
            f"{summary['avg_waiting']:.2f}",
            f"{summary['avg_turnaround']:.2f}",
            f"{summary['avg_response']:.2f}",
        )

    console.print(summary_table)


def _animate_result(result: ScheduleResult, delay: float) -> None:
    """
    Simple time-stepped textual simulation using the computed schedule.
    """
    console = Console()
    timeline = sorted(result.timeline, key=lambda s: (s.start_time, s.end_time))
    if not timeline:
        console.print("[red]No execution to animate.[/red]")
        return

    makespan = max(s.end_time for s in timeline)
    console.print(f"[bold]Simulating {result.algorithm}[/bold] (duration {makespan} time units)")
    console.print("[dim]Press Ctrl+C to skip animation.[/dim]")

    for t in range(makespan + 1):
        running = None
        for sl in timeline:
            if sl.start_time <= t < sl.end_time:
                running = sl.pid
                break
        bar = ""
        for sl in timeline:
            if sl.start_time <= t < sl.end_time:
                bar = f"[green]{'█' * (t - sl.start_time + 1)}[/green]"
                break
        msg = f"t={t:2d}: " + (running or "[idle]")
        console.print(msg + (" " + bar if bar else ""))
        time.sleep(delay)


def _interactive_menu(default_workload: str, default_quantum: int) -> None:
    console = Console()
    alg_choices = list(ALGORITHMS.keys())
    workload = default_workload
    quantum_default = default_quantum
    examples_dir = Path(__file__).resolve().parents[1] / "examples"
    runway_default = str(examples_dir / "runway_workload.json")

    def pick_workload(current: str) -> str:
        available = []
        if examples_dir.exists():
            available = sorted([p for p in examples_dir.glob("*.json")])
        console.print("\n[bold]Workload selection:[/bold]")
        for idx, p in enumerate(available, start=1):
            console.print(f"  [yellow]{idx}[/yellow]. [white]{p.name}[/white]")
        console.print(f"  [yellow]0[/yellow]. Keep current [green]{current}[/green]")
        choice = input(f"Choice [0-{len(available)}]: ").strip()
        if choice in {"", "0"}:
            return current
        try:
            idx = int(choice)
            if 1 <= idx <= len(available):
                return str(available[idx - 1])
        except ValueError:
            pass
        path_in = input("Enter workload path: ").strip()
        return path_in or current

    while True:
        console.print("\n[bold cyan]Scheduler CLI Menu[/bold cyan] [dim](q to quit)[/dim]")
        console.print(f"[bold]Current workload:[/bold] [green]{workload}[/green]")
        console.print("[bold]Select algorithm by number:[/bold]")
        for idx, alg in enumerate(alg_choices, start=1):
            console.print(f"  [yellow]{idx}[/yellow]. [white]{alg}[/white]")
        compare_current_idx = len(alg_choices) + 1
        compare_runway_idx = len(alg_choices) + 2
        console.print(f"  [yellow]{compare_current_idx}[/yellow]. [white]Compare (current workload)[/white]")
        console.print(f"  [yellow]{compare_runway_idx}[/yellow]. [white]Compare (runway workload)[/white]")

        choice = input(f"Choice [1-{compare_runway_idx} or q]: ").strip().lower()
        if choice in {"q", "quit", "exit"}:
            return

        try:
            alg_idx = int(choice) - 1
        except ValueError:
            console.print("[red]Invalid selection.[/red]")
            continue

        # Compare current workload
        if alg_idx == compare_current_idx - 1:
            q_val = quantum_default
            q_in = input(f"Quantum for rr/mlfq compare [{quantum_default}]: ").strip()
            if q_in:
                try:
                    q_val = int(q_in)
                except ValueError:
                    console.print("[red]Invalid quantum; using default.[/red]")
            try:
                wl_path = Path(workload)
                if not wl_path.exists():
                    console.print(f"[red]Workload not found: {workload}[/red]")
                    continue
                _run_compare(wl_path, q_val, console)
            except Exception as exc:  # noqa: BLE001
                console.print(f"[red]Error: {exc}[/red]")
            continue

        # Compare runway workload
        if alg_idx == compare_runway_idx - 1:
            q_val = quantum_default
            q_in = input(f"Quantum for rr/mlfq compare [{quantum_default}]: ").strip()
            if q_in:
                try:
                    q_val = int(q_in)
                except ValueError:
                    console.print("[red]Invalid quantum; using default.[/red]")
            try:
                wl_path = Path(runway_default)
                if not wl_path.exists():
                    console.print(f"[red]Runway workload not found: {runway_default}[/red]")
                    continue
                _run_compare(wl_path, q_val, console)
            except Exception as exc:  # noqa: BLE001
                console.print(f"[red]Error: {exc}[/red]")
            continue

        # Regular algorithm selection
        try:
            alg = alg_choices[alg_idx]
        except (ValueError, IndexError):
            console.print("[red]Invalid selection.[/red]")
            continue

        # Quick workload picker (examples or custom).
        change_wl = input("Change workload? [Enter=no, y=yes]: ").strip().lower()
        if change_wl == "y":
            workload = pick_workload(workload)

        quantum = quantum_default
        if alg in {"rr", "mlfq"}:
            q_in = input(f"Quantum for {alg} [{quantum_default}]: ").strip()
            if q_in:
                try:
                    quantum = int(q_in)
                except ValueError:
                    console.print("[red]Invalid quantum; using default.[/red]")

        animate = False
        animate_delay = 0.3
        animate_in = input("Animate this run? [Enter=no, y=yes]: ").strip().lower()
        if animate_in == "y":
            animate = True
            d_in = input(f"Step delay seconds [{animate_delay}]: ").strip()
            if d_in:
                try:
                    animate_delay = float(d_in)
                except ValueError:
                    console.print("[red]Invalid delay; using default.[/red]")

        try:
            wl_path = Path(workload)
            if not wl_path.exists():
                console.print(f"[red]Workload not found: {workload}[/red]")
                continue
            processes = load_workload(wl_path)
            result = run_algorithm(alg, processes, quantum=quantum)
             # optional step-by-step animation before summary
            if animate:
                try:
                    _animate_result(result, delay=animate_delay)
                except KeyboardInterrupt:
                    console.print("[yellow]Animation skipped.[/yellow]")
            _print_result(result)
            console.print("[dim]Run complete. Press Enter to return to menu...[/dim]")
            input()
        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]Error: {exc}[/red]")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    console = Console()

    if args.command == "run":
        workload_path = Path(args.workload)
        processes = load_workload(workload_path)
        result = run_algorithm(args.algorithm, processes, quantum=args.quantum)
        if args.step:
            try:
                _animate_result(result, delay=args.step_delay)
            except KeyboardInterrupt:
                console.print("[yellow]Animation skipped.[/yellow]")
        _print_result(result)
        return 0

    if args.command == "compare":
        workload_path = Path(args.workload)
        processes = load_workload(workload_path)

        summary_table = Table(title="Algorithm comparison", box=box.SIMPLE_HEAVY)
        summary_table.add_column("Algorithm")
        summary_table.add_column("Quantum", justify="right")
        summary_table.add_column("Avg waiting", justify="right")
        summary_table.add_column("Avg turnaround", justify="right")
        summary_table.add_column("Avg response", justify="right")

        for alg in args.algorithms:
            q = args.quantum if alg in {"rr", "mlfq"} else None
            result = run_algorithm(alg, processes, quantum=q)
            summary = summarize_process_metrics(result.processes)
            summary_table.add_row(
                result.algorithm,
                "" if result.quantum is None else str(result.quantum),
                f"{summary['avg_waiting']:.2f}",
                f"{summary['avg_turnaround']:.2f}",
                f"{summary['avg_response']:.2f}",
            )

        console.print(summary_table)
        return 0

    if args.command == "menu":
        _interactive_menu(args.workload, args.quantum)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())


