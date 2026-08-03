---
name: cc-create-agent-team
description: Create and manage Claude Code agent teams for parallel work. Use when coordinating multiple Claude instances, assigning independent work, or collecting parallel reviews.
---

# Create a Claude Code Agent Team

Use Claude Code agent teams only when independent parallel work will outweigh coordination cost.

## Prepare

1. Check `claude --version`; require Claude Code 2.1.32 or newer.
2. Confirm that agent teams are enabled in settings or the environment:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

3. Identify independent tasks, expected outputs, file ownership, and the completion condition.
4. Prefer ordinary subagents for simple, sequential, or tightly coupled work.

## Design the team

- Use three to five teammates for most tasks.
- Give each teammate a bounded assignment and enough context to work independently.
- Assign different files or subsystems to avoid edit conflicts.
- Require a plan before edits when the work is risky or ambiguous.
- Keep integration and final verification with the team lead.

Good candidates include parallel research, competing debugging hypotheses, cross-layer implementation, and multi-perspective review. Avoid teams for same-file edits, dependency-heavy sequences, or small focused tasks.

## Run and coordinate

1. Create the team and task list from the requested work.
2. Assign owners explicitly; do not rely on teammates discovering ownership.
3. Monitor the shared task list and mailbox.
4. Redirect stalled or overlapping work promptly.
5. Wait for every required teammate result before integrating.
6. Review all results, resolve conflicts, and run the combined verification.
7. Ask teammates to shut down, then clean up the team.

Use in-process display by default. Use split panes only when tmux or iTerm2 is available and separate terminals improve monitoring. Configure the mode with `claude --teammate-mode in-process` or the `teammateMode` setting.

## Constraints

- Only the lead can create a team; teammates cannot create nested teams.
- Each session manages one team at a time.
- Teammates inherit the lead's permission mode when spawned.
- In-process teammates do not support `/resume` or `/rewind`.
- Treat task status as advisory and verify delivered artifacts directly.
