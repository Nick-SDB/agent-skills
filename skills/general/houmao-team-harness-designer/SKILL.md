---
name: houmao-team-harness-designer
description: Design or iteratively revise a Houmao multi-agent team harness, including roles, topology, work routing, scheduling, state machines, mailbox contracts, persistence, runtime safeguards, and validation criteria. Use when a user asks for an early visual team proposal, a D0/D1/D2 harness design, a review of an existing team architecture, or the impact of changing a Houmao workflow. Keep design, artifact generation, launch, and live operation as separate approval boundaries.
---

# Houmao Team Harness Designer

Create an early, reviewable team design from incomplete requirements, then refine the same design as the user makes decisions. Treat the current output as a versioned design contract, not an interview transcript.

## Keep Authorization Boundaries Separate

Operate in design-only mode unless the user explicitly authorizes a later boundary.

1. Design the harness and revise its contracts.
2. Generate project files only after explicit artifact-generation approval.
3. Launch, stop, prompt, or clean up agents only after separate live-operation approval.
4. Monitor or mutate a running harness only when that live system is explicitly in scope.

Never interpret approval of a diagram or D2 dossier as approval to generate files or launch agents.

## Build the Design Incrementally

1. Establish the team objective, initial roles or capabilities, primary work flow, and completion condition. State safe assumptions for missing details.
2. Ask at most one material question at a time. Do not delay the first design for details that do not change its basic topology.
3. Publish a D0 concept as soon as the four minimum facts are known or explicitly assumed. Include Mermaid topology, workflow, and state-machine views.
4. Refine the accepted D0 into D1 contracts covering authority, routing, messages, transitions, concurrency, failures, recovery, and completion evidence.
5. Refine D1 into D2 only after prompts, runtime posture, persistence, operations, and acceptance tests are implementable.
6. Keep unresolved assumptions and questions visible. Do not label a design D2 while a mandatory state machine or transition owner is unresolved.

Read [references/interaction-and-maturity.md](references/interaction-and-maturity.md) for the design-session state machine, maturity criteria, and revision response contract.

## Use Portable Domain Concepts

Describe the reusable architecture with `work stream`, `work item`, `attempt`, `evidence`, `decision`, `dispatch queue`, and `completion policy`. Add a vocabulary map for the project's own terms. Do not make optimization-specific concepts such as `idea`, `candidate`, or `profile` universal.

Read [references/domain-model-and-vocabulary.md](references/domain-model-and-vocabulary.md) when defining roles, authority, ownership, completion evidence, or a domain vocabulary map.

## Select Explicit Topology and Scheduling

Choose and name a topology and scheduling policy instead of drawing an ambiguous network of roles. Define queue ownership, assignment rules, capacity, concurrency, backpressure, retries, in-flight work, draining, and completion races.

Read [references/topology-and-scheduling-patterns.md](references/topology-and-scheduling-patterns.md) when comparing pipelines, pools, fan-out/fan-in, hierarchical teams, batch barriers, or asynchronous refill.

## Specify States and Messages as Contracts

Include all three state-machine layers:

- design session;
- team lifecycle;
- work-item or worker lifecycle.

For every transition, name its source, event, guard, destination, single owner, persistence record, side effect, failure path, and recovery behavior. Keep diagrams, transition tables, role contracts, and mailbox subjects consistent.

Read [references/state-and-message-contracts.md](references/state-and-message-contracts.md) when writing state machines, transition tables, mailbox catalogs, identity rules, idempotency, or replay behavior.

## Define Runtime Safety Before D2

At D2, specify workspace isolation, credentials, model and reasoning posture, gateways, notifiers, persistent artifacts, preflight, liveness audits, stop behavior, cleanup, rerun rules, and failure evidence. Prefer observable controls and deterministic checks over assurances in role prompts.

Read [references/runtime-safety-and-validation.md](references/runtime-safety-and-validation.md) for runtime decisions, safety gates, validation scenarios, and acceptance-test coverage.

## Revise Without Restarting

When the user changes a requirement:

1. Answer the immediate question.
2. Revise only the affected design sections.
3. Show an impact delta with `Changed`, `Affected`, and `Unchanged` surfaces.
4. Update every affected Mermaid diagram and contract table.
5. List assumptions added, resolved, or invalidated.
6. Ask at most one next material question.

Name any conflict with an accepted decision before changing that decision.

## Produce and Validate the Dossier

Use [assets/team-harness-dossier-template.md](assets/team-harness-dossier-template.md) as the output skeleton. Adapt its examples and diagrams to the selected domain; do not return unresolved template markers.

When a dossier exists as Markdown, run:

```bash
python3 scripts/validate_team_harness_spec.py path/to/team-harness-dossier.md
```

Use [scripts/validate_team_harness_spec.py](scripts/validate_team_harness_spec.py) for structural checks only. Fix its errors before calling a design implementable, then perform human review for domain semantics, safety, and contradictions.

End a design-only task with the current maturity, unresolved decisions, and the exact next authorization boundary. Do not generate or launch anything merely to demonstrate the design.
