---
name: cc-create-agent-team
description: Design and scaffold a Claude Code agent team — a set of specialized subagents that collaborate on a task. Use when the user wants to build multiple agents that work together, split a workflow across roles, or set up parallel subagents for code review, research, refactoring, etc.
argument-hint: "[team-goal]"
---

# Create a Claude Code Agent Team

Guide the user through designing a team of specialized subagents, then scaffold the agent files. A good team has clear role separation, minimal tool permissions, and descriptions that trigger correct auto-delegation.

## Step 1 — Clarify the goal

If `$ARGUMENTS` is provided, treat it as the team's high-level goal. Otherwise ask:

1. **What is the team's overall job?** (e.g. "review PRs", "refactor a module", "investigate a production incident")
2. **Scope** — project-local (`.claude/agents/`) or personal (`~/.claude/agents/`)?
3. **Execution style** — should agents run **in parallel** (independent work) or **sequentially** (pipeline where one hands off to the next)?

## Step 2 — Propose the roster

Based on the goal, propose **2–5 agents**. Fewer is better: each agent should own a single, non-overlapping responsibility. Present the proposal as a table and let the user confirm or adjust before writing any files:

| Agent name | Responsibility | Tools | Model |
|------------|----------------|-------|-------|
| `security-reviewer` | Audit for auth, injection, secret-handling issues | Read, Grep, Glob | sonnet |
| `test-runner`       | Run the suite, surface failures and coverage gaps | Read, Bash, Glob | sonnet |
| `doc-writer`        | Update docs and examples to match code changes    | Read, Write, Edit | sonnet |

**Rules of thumb when proposing:**

- Each agent has **one** sentence of purpose. If you need "and" twice, split it.
- Grant the **minimum tools** needed. Read-only agents never get Write/Edit/Bash.
- Prefer `sonnet` by default; use `opus` only for deep reasoning tasks; `haiku` for cheap fast lookups.
- Avoid overlap — two agents writing to the same files in parallel will conflict.

## Step 3 — Write the agent files

For each confirmed agent, create a Markdown file at:

- Project scope: `.claude/agents/<agent-name>.md`
- Personal scope: `~/.claude/agents/<agent-name>.md`

### Agent file format

```markdown
---
name: <agent-name>
description: <when to delegate to this agent — start with a trigger phrase like "Use when…" or "Invoke to…". This is what Claude matches against to auto-delegate.>
tools: <comma-separated list, e.g. Read, Grep, Glob>
model: sonnet
---

You are a <role>. Your job is to <one-sentence responsibility>.

## Scope
- <what is in scope>
- <what is out of scope — explicitly list handoffs to other team members>

## Output format
Return a concise report with:
- <bullet 1>
- <bullet 2>

Keep the response under <N> words. Do not modify files unless Write/Edit are in your tools.
```

### Description field — the critical part

The `description` decides when Claude auto-delegates. Bad vs good:

- ❌ `"Reviews code"` — too vague, will fire on everything
- ✅ `"Use when auditing a diff or file for security issues: auth, injection, secret handling, unsafe deserialization"` — specific triggers

## Step 4 — Document the team

Create a short `.claude/agents/README.md` (or append to existing) describing:

- The team's goal
- Each member's role in one line
- How to invoke: explicit (`"use the security-reviewer agent on …"`) or by asking for parallel review
- Any ordering constraints (e.g. "run test-runner before doc-writer")

## Step 5 — Show the user how to run the team

Tell the user they can now:

1. **Parallel launch** (independent roles):
   > "Run security-reviewer, test-runner, and doc-writer in parallel on the current diff."

   Claude will emit multiple Agent tool calls in one message so they execute concurrently.

2. **Pipeline** (sequential handoff):
   > "Have test-runner check the build, then doc-writer update docs for any changed public APIs."

3. **Explicit single agent**:
   > "Use the security-reviewer agent on src/auth/."

## Best practices checklist

Before finishing, verify:

- [ ] Every agent's `description` starts with a clear trigger phrase
- [ ] No two agents share write access to the same files
- [ ] Read-only roles have no Bash/Write/Edit
- [ ] The team has ≤5 members (more = coordination overhead)
- [ ] Each agent returns a **short summary**, not full logs, to keep the main context lean
- [ ] A README documents the team so humans (and future Claude sessions) can discover it

## What to do

1. Clarify the goal, scope, and execution style (Step 1).
2. Propose the roster as a table and wait for confirmation (Step 2).
3. Create the directory: `mkdir -p <scope>/agents`
4. Write one `<agent-name>.md` per confirmed agent (Step 3).
5. Write or update `README.md` describing the team (Step 4).
6. Show the user the invocation examples (Step 5) and the checklist (best practices).
