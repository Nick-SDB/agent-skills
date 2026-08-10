# Domain Model and Vocabulary

## Portable concepts

Use these terms in the reusable architecture:

| Concept | Meaning |
|---|---|
| `work stream` | The bounded body of work the team advances. |
| `work item` | An independently routable unit of work. |
| `attempt` | One execution or revision of a work item. |
| `evidence` | Structured output used to evaluate an attempt. |
| `decision` | Acceptance, revision, rejection, blocking, or another domain result. |
| `dispatch queue` | Work items currently eligible for assignment. |
| `completion policy` | Evidence and authority required to terminate a work stream. |

Do not assume a work item is an idea, ticket, patch, sample, or candidate. Map those terms explicitly.

## Vocabulary map

Include a map in every dossier:

```yaml
domain_vocabulary:
  work_stream: support_campaign
  work_item: ticket
  attempt: response_draft
  evidence: resolution_check
  decision: support_lead_verdict
  dispatch_queue: triage_queue
  completion_policy: service_window_complete
```

Use `not_applicable` when a generic concept genuinely has no domain equivalent, and explain how its contract is otherwise satisfied. Never copy example values into an unrelated domain.

## Role contract

Specify each role with:

| Field | Requirement |
|---|---|
| Purpose | One outcome the role exists to produce. |
| Inputs | Accepted events, artifacts, and state views. |
| Outputs | Events, artifacts, evidence, or decisions produced. |
| Authority | States, queues, files, or decisions the role may commit. |
| Prohibited authority | Important actions reserved for another owner. |
| Capacity | Singleton, fixed pool, elastic pool, or bounded concurrency. |
| Failure behavior | Observable failure result and escalation target. |
| Recovery behavior | How work resumes after restart without duplication. |

Separate capability from authority. A reviewer may be capable of editing code while remaining unauthorized to merge it.

## Ownership matrix

Give each authoritative mutable object exactly one committing owner. Other roles may propose changes or emit evidence.

| Object | Single writer | Readers | Persistence | Conflict rule |
|---|---|---|---|---|
| Work-stream state | Coordinator | All roles | State record | Reject stale version. |
| Dispatch queue | Dispatcher | Coordinator, workers | Queue store | Compare-and-set assignment. |
| Attempt evidence | Worker | Verifier | Attempt artifact | Append-only by attempt ID. |
| Decision | Verifier | Coordinator, worker | Decision record | One final decision per attempt. |

Replace example roles and stores with project-specific ones. Flag any object with multiple writers unless the design defines an explicit consensus or transaction protocol.

## Identity model

Define stable identifiers before D1:

- `work_stream_id` identifies the overall run or bounded objective;
- `work_item_id` survives retries and reassignment;
- `attempt_id` changes for each execution or revision;
- `event_id` uniquely identifies a protocol delivery;
- `causation_id` points to the triggering event;
- `correlation_id` groups events for one work item or decision chain;
- `actor_id` names the role instance producing a mutation.

Distinguish semantic identity from process IDs, pane names, or temporary paths.

## Completion contract

Define all of the following:

1. who may propose completion;
2. what evidence is required;
3. who commits the terminal decision;
4. when new dispatch stops;
5. what happens to queued work;
6. how in-flight attempts drain, cancel, or report terminal failure;
7. where the completion decision is persisted;
8. how restart recognizes that completion already occurred.

Do not use `all workers idle` as the only completion condition; idleness can also mean deadlock, lost delivery, or missing work.
