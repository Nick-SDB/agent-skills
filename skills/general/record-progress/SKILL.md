---
name: record-progress
description: Append the current session's overall progress, state, and next steps to a durable PROGRESS.md so a fresh agent can quickly resume. Use when the user asks to 记录进度、存档进度、交接进度、写 PROGRESS、checkpoint, or when a durable resume point is needed so work survives a session crash.
---

# Record Progress

Maintain a durable, agent-readable `PROGRESS.md` at the repository root so a fresh agent can understand and resume the work even if the current session ends or crashes.

## When to record

- The user asks to record, checkpoint, or hand off progress.
- Before a risky or long-running operation, so a crash leaves a resume point.
- After a milestone or a background job completes, so the latest state is captured.
- When work spans many steps and the context is at risk of being lost.

## What to write

Create `PROGRESS.md` if absent; otherwise append under a new dated heading. Structure it in this order:

1. **Objective** — the goal being worked toward, in one or two sentences.
2. **Completed** — done items, each with its result or conclusion.
3. **In progress** — what is running now, including background jobs and their status; note anything that will be lost on crash.
4. **Next steps** — the immediate pending work, ordered.
5. **Key context** — decisions, constraints, and gotchas a fresh agent must know to avoid repeating mistakes (production files not to change, which baseline to use, which GPU to avoid, fixed toolchain versions).
6. **Artifacts** — paths to key files, docs, and results.

## Rules

- Write for an agent that has no conversation context: include concrete facts (numbers, file paths, decisions), never pronouns or "as above".
- Keep each bullet to one line: what changed and what it means.
- Append, do not overwrite earlier history, unless the user asks to rewrite.
- Prefer the repository's existing progress or docs convention if one exists; otherwise use the repository root.

## Quality check

Before finishing, verify that a fresh agent could, from `PROGRESS.md` alone, know the objective, what is done versus pending, what is running, the key constraints, and the artifact locations.
