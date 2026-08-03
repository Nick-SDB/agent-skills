---
name: cc-create-skill
description: Create a Claude Code skill with a focused SKILL.md and optional bundled resources. Use when adding a Claude slash command or reusable Claude Code workflow.
---

# Create a Claude Code Skill

Create a focused skill that follows the common Agent Skills layout and works from Claude Code's personal or project scope.

## Gather requirements

Determine:

1. The lowercase hyphenated skill name.
2. The workflow and concrete trigger phrases.
3. Personal scope (`~/.claude/skills/`) or project scope (`.claude/skills/`).
4. Whether the skill needs scripts, references, or assets.
5. How the user will verify the result.

Infer answers from the request when safe. Ask only for decisions that materially change the workflow.

## Create the skill

Use this structure:

```text
<scope>/skills/<skill-name>/
├── SKILL.md
├── scripts/       # optional deterministic helpers
├── references/    # optional on-demand documentation
└── assets/        # optional output resources
```

Write `SKILL.md` with exactly two frontmatter fields:

```yaml
---
name: skill-name
description: State what the skill does and the requests that should trigger it.
---
```

Write the body as concise imperative instructions. Keep platform-specific configuration outside the canonical frontmatter. Reference bundled files with relative paths and explain when to read or run them.

## Validate

1. Confirm the directory name matches `name`.
2. Confirm the description contains both purpose and trigger conditions.
3. Check every relative reference and exercise every added script.
4. Test automatic matching with a representative prompt.
5. Test explicit invocation with `/<skill-name>`.

Report the created files, validation performed, and the exact invocation to try.
