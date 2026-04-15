---
name: cc-create-agent-team
description: Design and scaffold a Claude Code agent team — a set of specialized subagents that collaborate on a task. Use when the user wants to build multiple agents that work together, split a workflow across roles, or set up parallel subagents for code review, research, refactoring, etc.
argument-hint: "[team-goal]"
---

# Create a Claude Code Agent Team

Guide the user through designing a team of specialized subagents, then scaffold the agent files. A good team has clear role separation, minimal tool permissions, and descriptions that trigger correct auto-delegation.

## Step 0 — Ensure agent-teams config is enabled (run this FIRST, always)

The `TeamCreate` / `SendMessage` tools are part of Claude Code's **experimental agent-teams** feature. It is **disabled by default** and must be turned on before the team can be launched. Additionally, display defaults to **tmux split panes** so each teammate gets its own visible window.

Do the following checks silently; only surface a problem to the user if something is missing.

### 0a. Version check

```bash
claude --version   # must be >= 2.1.32
```

If older, tell the user to upgrade and stop.

### 0b. Turn on the experimental flag in `~/.claude/settings.json`

Ensure this key exists (merge with existing content — do **not** overwrite other fields):

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

### 0c. Set tmux as the default display mode in `~/.claude.json`

`~/.claude.json` is Claude Code's global runtime config (separate from `settings.json`). Use a small Python snippet to merge safely — this file is large and contains many other keys, so never overwrite it:

```bash
python3 -c "
import json, shutil
p = '/home/USER/.claude.json'
shutil.copy(p, p + '.bak')
with open(p) as f: d = json.load(f)
d['teammateMode'] = 'tmux'
with open(p, 'w') as f: json.dump(d, f, indent=2)
"
```

### 0d. Verify the tmux prerequisite

```bash
which tmux && tmux -V           # must be installed
echo "${TMUX:-NOT_IN_TMUX}"      # user should already be inside a tmux session
```

- If tmux is missing: tell the user to install it (e.g. `apt install tmux`) and stop.
- If the user is **not** inside a tmux session: warn them that split-pane mode needs them to launch Claude Code from within `tmux`; offer to fall back to `teammateMode: "in-process"` if they prefer.

### 0e. Tell the user to restart

`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` and `teammateMode` are loaded at Claude Code startup. After writing the config, instruct the user to exit and relaunch `claude` (from inside tmux) before the team can actually be spawned. Team config created in the current session will still work, but new teammates won't appear in tmux panes until the restart.

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

1. **Enable agent-teams config and set tmux as default display mode (Step 0).** Do this first, every time — the feature is off by default and split-pane display must be explicitly configured.
2. Clarify the goal, scope, and execution style (Step 1).
3. Propose the roster as a table and wait for confirmation (Step 2).
4. Create the directory: `mkdir -p <scope>/agents`
5. Write one `<agent-name>.md` per confirmed agent (Step 3).
6. Write or update `README.md` describing the team (Step 4).
7. Show the user the invocation examples (Step 5) and the checklist (best practices).
