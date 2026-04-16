# atomic-worker-pipeline

Design and implement a multi-machine multi-GPU asynchronous parallel worker pipeline using atomic file operations for coordination.

---

## When to use

- The user needs to run a GPU-intensive task (inference, encoding, generation, eval) across many GPUs
- Tasks are independent and embarrassingly parallel (no inter-task dependencies)
- Workers may span multiple machines sharing a filesystem (NFS/GPFS/CIFS)
- No external broker (Redis, RabbitMQ, etc.) is available or desired
- The user says "parallel generation", "multi-GPU pipeline", "distributed workers", "atomic-rename queue"

## When NOT to use

- Tasks have ordering dependencies (use a DAG scheduler instead)
- The workload is a single model training (use DDP/FSDP instead)
- The shared filesystem doesn't support POSIX atomic rename (rare, but check)
- The user wants a persistent service (this is a batch-drain pattern, not a daemon)

---

## Core design pattern

```
${ROOT}/
├── pending/          # Task queue: one JSON file per task
├── claimed/          # In-flight: renamed from pending/ by a worker
├── done/             # Completed: output artifacts + _SUCCESS sentinel
├── failed/           # Dead-letter: tasks that exceeded max retries
└── _WORKERS.d/       # Heartbeat: one touch-file per live worker
```

**Coordination protocol — zero-broker, POSIX-only:**

1. **Claim**: `os.rename(pending/X.json, claimed/X.<worker_id>.<timestamp>.json)`
   - POSIX rename is atomic — exactly one worker wins
   - Losers get `FileNotFoundError`, catch and try next task
   - Worker ID = `{hostname}_gpu{cuda_device}_{pid}`

2. **Execute**: Worker loads task JSON, runs the GPU work, writes output to a temp path

3. **Commit**: `os.rename(output.tmp, done/X/output.ext)` then delete claimed entry
   - Temp-then-rename ensures no partial outputs are visible

4. **Retry**: On failure, increment `task.attempts`. If < max_attempts, rename back to `pending/`. If >= max_attempts, move to `failed/` with error log.

5. **Heartbeat**: Daemon thread touches `_WORKERS.d/{worker_id}` every 60s. A separate watchdog can detect stale claims by checking heartbeat age.

**Why this works across machines:** POSIX `rename()` on the same filesystem is atomic even over NFS (NFSv3+ with `close-to-open` consistency, NFSv4 natively). No lock files, no coordination service, no port listening.

---

## Implementation steps

### Step 1: Understand the task

Ask the user:
1. **What is each task?** (e.g., "generate a video from a prompt", "encode a video to latent")
2. **What is the input?** (e.g., prompt string, video file path, latent tensor)
3. **What is the output?** (e.g., .mp4 file, .pt tensor, JSON metrics)
4. **What GPU resource does each task need?** (one model load, then loop? or load per task?)
5. **Where is the shared filesystem root?**

### Step 2: Design the task JSON schema

Each task is a self-contained JSON file in `pending/`. Design it to contain everything a worker needs:

```json
{
  "id": "task_001",
  "prompt": "A cat playing piano...",
  "seed": 42,
  "resolution": [832, 480],
  "num_frames": 81,
  "attempts": 0
}
```

Rules:
- `id` is the primary key (used in file naming, output directory)
- `attempts` starts at 0, incremented on retry
- Include all parameters so the worker is stateless — it reads the JSON and has everything

### Step 3: Implement the init script (or subcommand)

Creates `pending/` tasks from a user-provided input (prompts file, video list, etc.).

```python
def init_tasks(input_path, root):
    for item in parse_input(input_path):
        task = {"id": item.id, ..., "attempts": 0}
        tmp = root / "pending" / f"{task['id']}.json.tmp"
        final = root / "pending" / f"{task['id']}.json"
        if final.exists():
            continue  # idempotent
        with open(tmp, "w") as f:
            json.dump(task, f)
        os.rename(str(tmp), str(final))
```

Key: write to `.tmp` then rename — even init is crash-safe.

### Step 4: Implement the worker

One Python script, one GPU per process. Structure:

```python
def main():
    # 1. Load model ONCE (expensive, do it before the loop)
    model = load_model(checkpoint_dir)

    # 2. Start heartbeat thread
    heartbeat = HeartbeatThread(workers_dir / worker_id, interval=60)
    heartbeat.start()

    # 3. Claim-execute loop
    while not shutdown_requested:
        result = claim_task(pending, claimed, worker_id)
        if result is None:
            time.sleep(idle_seconds)
            continue
        claimed_path, task = result
        try:
            output = model.run(task)
            save_output(output, done_dir / task["id"])
            os.unlink(str(claimed_path))
        except Exception:
            handle_failure(task, claimed_path, pending, failed, max_attempts)

    # 4. Cleanup
    heartbeat.stop()
```

#### Claim function (critical path):

```python
def claim_task(pending, claimed, worker_id):
    for entry in sorted(os.listdir(pending)):
        if not entry.endswith(".json"):
            continue
        src = pending / entry
        task_id = entry.replace(".json", "")
        dst = claimed / f"{task_id}.{worker_id}.{int(time.time()*1000)}.json"
        try:
            os.rename(str(src), str(dst))
            with open(dst) as f:
                return dst, json.load(f)
        except FileNotFoundError:
            continue  # another worker got it
    return None
```

#### Failure handler:

```python
def handle_failure(task, claimed_path, pending, failed, max_attempts):
    task["attempts"] += 1
    if task["attempts"] >= max_attempts:
        fail_dir = failed / task["id"]
        fail_dir.mkdir(parents=True, exist_ok=True)
        with open(fail_dir / "task.json", "w") as f:
            json.dump(task, f)
        with open(fail_dir / "error.log", "w") as f:
            f.write(traceback.format_exc())
    else:
        # Return to pending for retry
        tmp = pending / f"{task['id']}.json.tmp"
        final = pending / f"{task['id']}.json"
        with open(tmp, "w") as f:
            json.dump(task, f)
        os.rename(str(tmp), str(final))
    try:
        os.unlink(str(claimed_path))
    except FileNotFoundError:
        pass
```

### Step 5: Implement the launcher script

Bash script that auto-detects GPUs and spawns one worker per card:

```bash
#!/bin/bash
set -euo pipefail
ROOT="${1:?Usage: $0 <root>}"
NUM_GPUS=$(nvidia-smi -L 2>/dev/null | wc -l)
PIDS=()
for GPU in $(seq 0 $((NUM_GPUS - 1))); do
    CUDA_VISIBLE_DEVICES=$GPU python worker.py --root "$ROOT" &
    PIDS+=($!)
    echo "GPU $GPU: pid=$!"
done
echo "Stop all: kill ${PIDS[*]}"
wait
```

**Important bash rule:** Never use `pid=$(func &)` — the `&` runs in a subshell and `wait` won't work. Always background directly in the parent shell.

### Step 6: Implement the status script (or subcommand)

```python
def status(root):
    pending = count(root / "pending", "*.json")
    claimed = count(root / "claimed", "*.json")
    done = count(root / "done", "*")
    failed = count(root / "failed", "*")
    print(f"pending: {pending}  claimed: {claimed}  done: {done}  failed: {failed}")
```

### Step 7: (Optional) Implement the watchdog

Recovers stale claims from crashed workers:

```python
def watchdog(root, stale_threshold=600):
    for claimed_file in (root / "claimed").glob("*.json"):
        # Parse worker_id from filename
        # Check _WORKERS.d/{worker_id} mtime
        # If heartbeat older than threshold, return task to pending
```

---

## Subcommand pattern (recommended)

Use a single script with subcommands rather than separate files:

```
worker.py --root DIR init --input prompts.json
worker.py --root DIR work [--ckpt-dir ...] [--max-attempts 3]
worker.py --root DIR status
```

This keeps everything in one file and makes the CLI discoverable.

---

## Checklist for the implementer

- [ ] Task JSON is self-contained (worker needs no external state)
- [ ] All file writes use tmp-then-rename (crash-safe)
- [ ] Claim uses `os.rename` + catch `FileNotFoundError` (atomic, no locks)
- [ ] Worker loads model once before the loop (not per-task)
- [ ] Heartbeat thread runs in daemon mode
- [ ] Signal handler (SIGTERM/SIGINT) sets a flag, exits after current task
- [ ] Failure handler returns task to pending if attempts < max
- [ ] Launcher uses direct `&` backgrounding (no subshell trap)
- [ ] Status subcommand exists
- [ ] `OVERRIDE_STEPS` or equivalent env var for testing (e.g., 1-step inference)
- [ ] Disk space check before starting worker

---

## Examples in this codebase

Two working implementations of this pattern:

1. **`scripts/distillation-dataset/worker.py`** — Wan T2V generation with latent capture for distillation dataset. Has watchdog, status, launcher. The reference implementation.

2. **`scripts/benchmarks/vbench2/generate_videos.py`** — VBench 2.0 video generation with subcommand pattern (init/work/status in one file). Simpler variant.

Both use the same protocol and can run on the same shared filesystem with any number of machines.
