---
name: atomic-worker-pipeline
description: Design a broker-free asynchronous worker pipeline over a shared filesystem. Use for independent multi-machine or multi-GPU batch tasks that need atomic claiming, retries, heartbeats, and crash-safe outputs.
---

# Build an Atomic Worker Pipeline

Use this pattern only for independent batch tasks on a shared filesystem that guarantees atomic rename within one filesystem. Use a DAG scheduler for dependent tasks and DDP or FSDP for coordinated model training.

## Define the protocol

Create this state layout:

```text
<root>/
├── pending/       # one self-contained task file per item
├── claimed/       # atomically renamed in-flight tasks
├── done/          # committed outputs and success sentinels
├── failed/        # exhausted tasks and error records
└── workers/       # one heartbeat per live worker
```

Use a stable task identifier and include every execution parameter plus an attempt counter in the task record. Keep workers stateless apart from the shared directories.

## Implement claiming

1. List eligible files in `pending/` deterministically.
2. Rename one task to `claimed/<task>.<worker>.<timestamp>.json`.
3. Treat a missing-source error as a lost race and try the next task.
4. Do not use check-then-move logic or lock files.

```python
def claim_task(pending, claimed, worker_id):
    for source in sorted(pending.glob("*.json")):
        destination = claimed / f"{source.stem}.{worker_id}.{time.time_ns()}.json"
        try:
            source.rename(destination)
            return destination, json.loads(destination.read_text())
        except FileNotFoundError:
            continue
    return None
```

## Execute and commit

1. Load expensive models or resources once before the worker loop.
2. Start a heartbeat that updates `workers/<worker-id>` periodically.
3. Process the claimed task.
4. Write output to a temporary path on the same filesystem.
5. Flush and atomically rename the completed output into `done/`.
6. Write a success sentinel when multiple output files form one result.
7. Remove the claimed task only after the result is durable.

On failure, increment the attempt counter. Atomically return the task to `pending/` below the retry limit; otherwise move it to `failed/` with the task record and traceback. Preserve the original failure if cleanup also fails.

## Recover crashed workers

Use a watchdog only after defining heartbeat and claim timeouts. Recover a claim when both its age and the owning worker's stale heartbeat prove abandonment. Make recovery idempotent and record why the claim was returned.

## Launch and stop

Launch one process per assigned GPU and background processes directly in the parent shell:

```bash
CUDA_VISIBLE_DEVICES="$gpu" python worker.py --root "$root" work &
pids+=("$!")
```

Do not capture a background process through command substitution; that prevents reliable parent-shell waiting. Handle SIGTERM and SIGINT by finishing or safely returning the active task before exit.

## Verify

- Race multiple workers for one task and confirm exactly one claim succeeds.
- Kill a worker during execution and confirm watchdog recovery.
- Kill a worker during output writing and confirm no partial result is visible.
- Exercise retries, exhausted failures, restart idempotence, and low-disk handling.
- Provide `init`, `work`, and `status` subcommands and a short-step test mode.
