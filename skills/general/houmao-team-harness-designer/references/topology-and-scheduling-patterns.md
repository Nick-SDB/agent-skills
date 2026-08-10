# Topology and Scheduling Patterns

## Choose topology from control needs

Select the smallest topology that gives every queue, decision, and state an owner.

| Pattern | Prefer when | Main risk | Required control |
|---|---|---|---|
| Pipeline | Work passes through ordered stages. | A slow stage blocks the stream. | Per-stage capacity and backpressure. |
| Fan-out/fan-in | Independent attempts can run in parallel and be aggregated. | Duplicate or late results corrupt aggregation. | Stable attempt IDs and aggregation cutoff. |
| Worker pool | Similar items share interchangeable workers. | Starvation or unfair assignment. | Queue policy, leases, and capacity limits. |
| Hierarchical | Subteams need local coordination under global policy. | Conflicting authority across levels. | Explicit delegation and escalation boundaries. |
| Peer collaboration | Work requires negotiation without a permanent coordinator. | Split brain and circular waiting. | Decision protocol and deadlock recovery. |

Draw control flow separately from data or artifact flow when one diagram would hide ownership.

## Scheduling policies

### Batch barrier

Dispatch a bounded batch, wait until every required result reaches the barrier, then make a batch-level decision.

Use when cross-item comparison is required. Define missing-result timeout, partial-batch policy, retry limits, and barrier owner. Do not describe the team as asynchronous when every worker still waits at a global barrier.

### Asynchronous refill

Dispatch a replacement whenever capacity becomes available. Process results independently unless a decision explicitly requires aggregation.

Use for throughput and heterogeneous task duration. Define queue serialization, capacity accounting, duplicate completion handling, and the race between final completion and late refill.

### Priority queue

Order eligible items by explicit priority and tie-break rules. Add aging or quotas when lower-priority work must make progress.

### Work stealing

Allow idle workers to claim work from another queue. Define lease transfer, ownership version, and recovery after a claimant disappears.

## Scheduling contract

Specify:

- queue owner and authoritative persistence;
- eligibility and priority calculation;
- assignment event and acceptance handshake;
- lease duration, heartbeat, and expiry;
- maximum global and per-role concurrency;
- resource or credential constraints;
- backpressure threshold and producer behavior;
- retry budget and reassignment rules;
- fairness and starvation prevention;
- queued and in-flight behavior during draining;
- terminal handling for late or duplicate results.

## Common race: refill versus completion

Use an atomic or serialized rule equivalent to:

```text
if completion_committed:
    reject_new_dispatch
elif capacity_available and eligible_work_exists:
    reserve_capacity_and_dispatch
```

Do not let one role commit completion while another independently dispatches from a stale view. Persist a version or epoch that both operations check.

## Backpressure

Prefer observable thresholds over prompt-only guidance. Examples:

- stop producing when queue depth reaches a bound;
- stop dispatch when an evidence store is unavailable;
- reserve per-role concurrency before sending work;
- reduce refill rate after repeated timeout or rejection;
- enter `Draining` before terminal completion.

Define the event that clears backpressure and the owner permitted to resume dispatch.

## Diagram checklist

For each topology or workflow diagram, verify:

- arrows have semantic labels;
- queue and state owners are visible;
- control and evidence paths are distinguishable;
- rejection, blocking, timeout, and recovery paths are not omitted;
- completion stops new dispatch;
- in-flight work has an explicit drain, cancellation, or terminal-report path.
