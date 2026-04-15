---
name: cc-create-skill
description: Create a new Claude Code custom skill (slash command). Use when the user wants to make a new skill, add a slash command, or scaffold a SKILL.md file.
argument-hint: "[skill-name]"
---

# Create a Claude Code Skill

Help the user create a new custom skill (slash command) for Claude Code.

## Gather requirements

Ask the user (if not already clear from context or $ARGUMENTS):

1. **Skill name** — lowercase, hyphens, no spaces (e.g. `fix-issue`, `deploy`, `lint-pr`). Use $ARGUMENTS as the name if provided.
2. **What should it do?** — a short description of the skill's purpose.
3. **Scope** — personal (`~/.claude/skills/`) or project-local (`.claude/skills/`)?
4. **Should Claude auto-invoke it?** — or only when the user types the slash command?
5. **Does it take arguments?** — if so, what kind (e.g. `[filename]`, `[issue-number]`)?

## Skill file structure

Every skill lives in its own directory with a `SKILL.md` entrypoint:

```
<scope>/skills/<skill-name>/
├── SKILL.md          # required — frontmatter + instructions
├── reference.md      # optional — detailed docs, loaded on-demand
├── examples.md       # optional — usage examples
└── scripts/          # optional — helper scripts
```

### Scope paths

| Scope    | Path                                     |
|----------|------------------------------------------|
| Personal | `~/.claude/skills/<name>/SKILL.md`       |
| Project  | `.claude/skills/<name>/SKILL.md`         |

## SKILL.md format

```yaml
---
name: <skill-name>
description: <what it does and when to use it — be specific, Claude uses this to decide relevance>
# Optional fields below:
disable-model-invocation: false   # true = only user can invoke via /command
user-invocable: true              # false = hidden from / menu, only Claude invokes
argument-hint: "[arg-description]"
allowed-tools: Bash(git *) Read   # tools auto-approved without permission prompts
context: fork                     # run in isolated subagent (fork) or inline (default)
agent: Explore                    # subagent type when context: fork
model: sonnet                     # model override (opus, sonnet, haiku)
effort: high                      # effort level (low, medium, high, max)
paths: "**/*.py"                  # only activate for matching files
shell: bash                       # shell for inline commands (bash or powershell)
---

# Skill Title

Markdown instructions for Claude to follow when this skill is invoked.
Use $ARGUMENTS to reference what the user passed after the /command.
Use $0, $1, etc. for positional arguments.
```

## Variable substitutions available in skill body

| Variable              | Expands to                              |
|-----------------------|-----------------------------------------|
| `$ARGUMENTS`          | Everything after `/skill-name `         |
| `$ARGUMENTS[N]` / `$N` | Specific positional argument (0-based) |
| `${CLAUDE_SESSION_ID}` | Current session ID                     |
| `${CLAUDE_SKILL_DIR}` | Directory containing this SKILL.md     |

## Dynamic context — run shell commands at load time

Inline a command result with `` !`command` ``:

```markdown
Current branch: !`git branch --show-current`
```

Multi-line block:

````markdown
```!
git status --short
npm test -- --listTests
```
````

These execute **before** Claude sees the skill content. The output replaces the command.

## Frontmatter field reference

| Field                    | Default | Purpose                                                    |
|--------------------------|---------|------------------------------------------------------------|
| `name`                   | dirname | Slash command name. Lowercase + hyphens only, max 64 chars |
| `description`            | —       | When/why to use. Claude reads this to decide relevance     |
| `disable-model-invocation` | false | If true, only `/command` works — Claude won't auto-trigger |
| `user-invocable`         | true    | If false, hidden from `/` menu — only Claude can load it   |
| `argument-hint`          | —       | Shown in autocomplete (e.g. `[issue-number]`)              |
| `allowed-tools`          | —       | Space-separated tools approved without prompting            |
| `context`                | —       | `fork` for isolated subagent execution                     |
| `agent`                  | —       | Subagent type with `context: fork`                         |
| `model`                  | —       | Model override (opus, sonnet, haiku)                       |
| `effort`                 | —       | low, medium, high, max                                     |
| `paths`                  | —       | Glob patterns restricting activation                       |
| `shell`                  | bash    | Shell for `!` commands                                     |

## What to do

1. Collect the requirements above (or infer from context).
2. Create the directory: `mkdir -p <scope>/skills/<skill-name>`
3. Write `SKILL.md` with appropriate frontmatter and clear instructions.
4. If the skill is complex, create supporting `.md` files referenced from SKILL.md.
5. Tell the user to type `/<skill-name>` to test it.
