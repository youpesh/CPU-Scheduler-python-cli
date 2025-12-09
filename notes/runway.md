## Runway scheduling scenario

Workload file: `examples/runway_workload.json`

Interpretation:
- `burst_time` = runway occupancy time for a takeoff/landing.
- `priority` (lower is higher priority): emergency < passenger < cargo.
- Arrival times are when the aircraft is ready for the runway.

Suggested comparisons:

```bash
python -m scheduler_cli run --algorithm fcfs --workload examples/runway_workload.json
python -m scheduler_cli run --algorithm priority --workload examples/runway_workload.json
python -m scheduler_cli run --algorithm mlfq --quantum 2 --workload examples/runway_workload.json
python -m scheduler_cli compare --workload examples/runway_workload.json --quantum 2
```

Talking points for the report:
- **Fairness vs. urgency**: Priority scheduling should favor EMERGENCY_E; FCFS may delay it unfairly.
- **Turnaround and waiting**: Compare averages; note whether lower-priority (cargo) suffers starvation.
- **Throughput vs. preemption**: MLFQ may reduce response for short jobs; check if it helps urgent flights without starving long ones.


