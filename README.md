# agent-skills

A collection of custom skills (slash commands) for [Claude Code](https://claude.ai/code).

## Skills

### General

| Skill | Description |
|---|---|
| `atomic-worker-pipeline` | Design and implement a multi-machine multi-GPU async parallel worker pipeline using atomic file operations for coordination |
| `fix-locale` | Detect and fix UTF-8/locale issues causing CJK characters to display as underscores or question marks |
| `install-openspec` | Install and initialize OpenSpec (spec-driven development framework for AI coding assistants) |
| `project-code-map` | Scaffold `CLAUDE.md` + `docs/code_map.md` agent-entry documentation in a project |
| `sync-and-ship` | Sync the project's documentation index with the actual file tree, then commit and push |
| `tmux-mouse-scroll` | Enable mouse wheel scrolling in tmux sessions |
| `update-skill` | Update a skill in the cc-switch config directory and this repo, then commit and push |

### Claude Code

| Skill | Description |
|---|---|
| `cc-create-agent-team` | Design and scaffold a Claude Code agent team — specialized subagents that collaborate on a task |
| `cc-create-skill` | Create a new Claude Code custom skill (slash command) and scaffold its `SKILL.md` |
| `cc-skip-permissions` | Set up a shell alias so Claude Code skips all permission prompts |

## Usage

Skills live under `skills/<category>/<skill-name>/SKILL.md`. Install them via [cc-switch](https://github.com/Nick-SDB/cc-switch) or copy them into `~/.claude/skills/`.
