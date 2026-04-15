---
name: cc-create-agent-team
description: Create and manage Claude Code agent teams for parallel work. Use when user wants to coordinate multiple Claude instances, spawn teammates, or delegate work to a team.
argument-hint: "[team-description]"
---

# Create Agent Team

Help the user create and manage Claude Code agent teams for parallel work.

## ⚠️ Prerequisites: Enable Agent Teams First

Agent teams are experimental and **disabled by default**. You MUST enable them before use:

**In settings.json (recommended):**

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

Or set as an environment variable in your shell:

```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

> **Important:** Agent teams require Claude Code v2.1.32 or higher. Check with `claude --version`

## When to Use Agent Teams

Agent teams are best for parallel exploration tasks where multiple perspectives add value:

- **Research & Review**: Multiple teammates investigate different aspects simultaneously
- **New Features**: Teammates work on independent parts without interference
- **Debugging with Competing Hypotheses**: Parallel investigation of different theories
- **Cross-layer Coordination**: Frontend, backend, and testing changes in parallel

**Don't use agent teams for:**
- Sequential tasks
- Same-file edits
- Work with many dependencies
- Simple, focused tasks (use subagents instead)

## How Agent Teams Work

| Component | Role |
|-----------|------|
| **Team Lead** | Main Claude session that creates, generates, and coordinates teammates |
| **Teammates** | Independent Claude Code instances handling assigned tasks |
| **Task List** | Shared work items that teammates claim and complete |
| **Mailbox** | Message system for inter-agent communication |

## Display Modes

- **In-process** (default): All teammates run in your main terminal. Use Shift+Down to cycle through teammates and send messages directly.
- **Split panes**: Each teammate gets their own pane (requires tmux or iTerm2).

To override the default mode:

```json
// In ~/.claude.json (global config)
{
  "teammateMode": "in-process"
}
```

Or use the CLI flag:

```bash
claude --teammate-mode in-process
```

## Usage Examples

### Basic Team Creation

```
I'm designing a CLI tool that helps developers track TODO comments across
their codebase. Create an agent team to explore this from different angles: one
teammate on UX, one on technical architecture, one playing devil's advocate.
```

### With Specific Configuration

```
Create a team with 4 teammates to refactor these modules in parallel.
Use Sonnet for each teammate.
```

### Requiring Plan Approval

```
Spawn an architect teammate to refactor the authentication module.
Require plan approval before they make any changes.
```

### Parallel Code Review

```
Create an agent team to review PR #142. Spawn three reviewers:
- One focused on security implications
- One checking performance impact
- One validating test coverage
Have them each review and report findings.
```

## Controlling the Team

- **Direct communication**: Use Shift+Down to cycle to a teammate and type to send messages
- **Assign tasks**: Tell the lead to assign specific tasks to specific teammates
- **Close teammates**: `Ask the researcher teammate to shut down`
- **Clean up**: `Clean up the team` when done (run this through the lead, not teammates)

## Best Practices

1. **Start small**: 3-5 teammates is optimal for most workflows
2. **Give enough context**: Include specific details in your spawn prompt
3. **Avoid file conflicts**: Structure work so each teammate owns different files
4. **Monitor progress**: Check teammate progress and redirect when needed
5. **Wait for completion**: Tell the lead to "Wait for your teammates to complete their tasks before proceeding"

## Known Limitations

- In-process teammates don't support session recovery (`/resume`, `/rewind`)
- Task status may lag; manually update if tasks get stuck
- Each session can only manage one team at a time
- Teammates cannot spawn their own teams (only the lead can)
- All teammates inherit the lead's permission mode at spawn time