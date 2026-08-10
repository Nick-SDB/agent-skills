# Runtime Safety and Validation

## Separate design from operation

Keep four distinct boundaries:

1. design and review;
2. artifact generation;
3. launch, stop, cleanup, or rerun;
4. monitoring and mutation of a live run.

Require explicit authorization at each new boundary. Scope authorization to named files, projects, sessions, or runs.

## D2 runtime posture

Record these decisions even when the answer is `not applicable`:

| Surface | Questions to resolve |
|---|---|
| Model and reasoning | Which roles use which model, effort, limits, and fallback? |
| Credentials | Which role receives each credential and by what least-privilege path? |
| Workspace | Shared tree, isolated worktrees, containers, or remote sandboxes? |
| Gateway | How are model, network, or tool calls routed and audited? |
| Notifier | Which events are externalized, deduplicated, and rate-limited? |
| Persistence | Which state, queue, message, evidence, and decision records survive restart? |
| Runtime identity | How are roles and attempts mapped to processes without using process IDs as semantic identity? |
| Resource limits | What bounds concurrency, time, memory, storage, and external requests? |

Prefer enforced runtime controls over prompt-only restrictions.

## Preflight contract

Before launch, verify:

- the design maturity and approval record;
- role definitions and unique authoritative owners;
- project and workspace paths;
- required binaries, models, gateways, and credentials;
- mailbox subjects and recipient resolution;
- persistence schema and write access;
- concurrency and resource limits;
- stop and cleanup commands or APIs;
- recovery from an interrupted prior run;
- absence or explicit adoption of conflicting live sessions.

Define which failures block launch and which may proceed with a recorded warning.

## Runtime audit

Monitor evidence rather than relying only on role self-reports:

- queue depth, assignment age, and capacity reservations;
- state version progress and stale ownership leases;
- message delivery, retries, duplicates, and dead letters;
- attempt duration and heartbeat age;
- evidence and decision counts by terminal outcome;
- unexpected process, workspace, or credential access;
- completion proposal, dispatch stop, and drain progress.

Give every alert an owner, threshold, persisted observation, and recovery action.

## Stop, cleanup, and rerun

Define graceful and forced stop separately.

- Graceful stop enters `Draining`, rejects new dispatch, and waits or times out in-flight work.
- Forced stop records unresolved work and preserves enough evidence for reconciliation.
- Cleanup names exactly which runtime handles, temporary artifacts, workspaces, or credentials may be removed.
- Rerun either resumes the same work stream with durable identity or starts a new stream with an explicit lineage link.

Never make cleanup depend on broad globs or unresolved paths.

## Acceptance tests

Cover at least:

1. happy-path work from queue to terminal decision;
2. assignment rejection and successful reassignment;
3. blocked work and recovery or terminal escalation;
4. processing timeout and retry-budget exhaustion;
5. duplicate, delayed, reordered, and undeliverable messages;
6. stale owner or coordinator restart with idempotent replay;
7. completion racing with asynchronous refill;
8. graceful drain with in-flight work;
9. forced stop and subsequent reconciliation;
10. domain vocabulary in a non-optimization team;
11. unauthorized artifact generation or launch being refused;
12. mismatch detection across diagrams, transitions, roles, and messages.

For each test, define inputs, expected states, expected persistent evidence, forbidden side effects, and pass/fail criteria.

## Failure evidence

Require enough information to distinguish a design flaw from a runtime or dependency failure:

- work-stream, item, attempt, event, and actor IDs;
- source and expected state versions;
- triggering event and guard outcome;
- owner and runtime handle mapping;
- persisted error class and bounded diagnostic text;
- retry count and next allowed action;
- artifact or log references without embedded secrets;
- terminal decision or unresolved status.

Do not require secrets, full prompts, or unrelated user data in failure evidence.

## Final review

Before calling the dossier implementable, confirm:

- every authoritative mutable object has one owner;
- every non-terminal state can progress or fail explicitly;
- every protocol subject maps to a transition or documented notification;
- retries and replay are idempotent;
- completion stops dispatch and drains in-flight work;
- runtime controls are observable and enforceable;
- validation covers negative and recovery paths;
- artifact generation and launch remain separately authorized.
