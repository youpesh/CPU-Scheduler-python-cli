from __future__ import annotations

from typing import Dict, List

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .models import ScheduledSlice


def render_gantt(slices: List[ScheduledSlice]) -> str:
    """
    Legacy plain-text Gantt chart renderer (kept for reference / testing).
    """
    if not slices:
        return "(no execution)"

    slices = sorted(slices, key=lambda s: (s.start_time, s.end_time))

    line = "|"
    labels = ""
    time_marks = "0"
    last_time = 0

    for sl in slices:
        idle_gap = sl.start_time - last_time
        if idle_gap > 0:
            line += "." * idle_gap
            labels += " " * idle_gap
            last_time = sl.start_time
            time_marks += f"{last_time:>3}"

        width = max(1, sl.end_time - sl.start_time)
        line += "=" * width
        label = sl.pid[: width].ljust(width)
        labels += label
        last_time = sl.end_time
        time_marks += f"{last_time:>3}"

    line += "|"

    return "\n".join(
        [
            "Gantt Chart:",
            line,
            labels,
            time_marks,
        ]
    )


def build_rich_gantt(slices: List[ScheduledSlice]) -> tuple[Panel, str]:
    """
    Build a Rich Panel containing a colored Gantt chart and a string with time marks.
    """
    if not slices:
        panel = Panel("No execution", title="Gantt Chart")
        return panel, ""

    slices = sorted(slices, key=lambda s: (s.start_time, s.end_time))

    colors = ["red", "green", "yellow", "blue", "magenta", "cyan"]
    pid_to_color: Dict[str, str] = {}

    def pid_color(pid: str) -> str:
        if pid not in pid_to_color:
            idx = len(pid_to_color) % len(colors)
            pid_to_color[pid] = colors[idx]
        return pid_to_color[pid]

    timeline = Text()
    labels = Text()
    time_marks = "0"
    last_time = 0

    for sl in slices:
        idle_gap = sl.start_time - last_time
        if idle_gap > 0:
            timeline.append(" " * idle_gap)
            labels.append(" " * idle_gap)
            last_time = sl.start_time
            time_marks += f"{last_time:>3}"

        width = max(1, sl.end_time - sl.start_time)
        color = pid_color(sl.pid)

        timeline.append(" " * width, style=f"on {color}")
        labels.append(sl.pid[: width].ljust(width), style="bold")

        last_time = sl.end_time
        time_marks += f"{last_time:>3}"

    table = Table.grid(padding=(0, 0))
    table.add_row(timeline)
    table.add_row(labels)

    panel = Panel.fit(table, title="Gantt Chart")
    return panel, time_marks

