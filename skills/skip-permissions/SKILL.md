---
name: skip-permissions
description: Set up a shell alias so Claude Code skips all permission prompts. Use when the user wants to run Claude Code without interactive permission approvals, e.g. for automation, scripting, or unattended usage.
disable-model-invocation: true
argument-hint: "[shell]"
---

# Skip Permissions Setup

Set up an alias that lets Claude Code run without permission prompts by combining the `IS_SANDBOX=1` environment variable with the `--dangerously-skip-permissions` flag.

## What to do

Detect the user's shell (or use $ARGUMENTS if provided) and add the alias to the correct rc file.

**The alias:**
```bash
alias claude='IS_SANDBOX=1 claude --dangerously-skip-permissions'
```

### Steps

1. Determine the target shell. If `$ARGUMENTS` is provided (e.g. `bash`, `zsh`, `fish`), use that. Otherwise detect from `$SHELL`.
2. Pick the rc file:
   - `bash` -> `~/.bashrc`
   - `zsh`  -> `~/.zshrc`
   - `fish` -> `~/.config/fish/config.fish` (use fish syntax: `alias claude 'IS_SANDBOX=1 claude --dangerously-skip-permissions'`)
3. Check if the alias already exists in the rc file. If it does, tell the user it's already configured and stop.
4. Append the alias to the end of the rc file.
5. Tell the user to run `source <rc-file>` or open a new terminal to activate it.

### Important notes

- Warn the user that `--dangerously-skip-permissions` disables ALL permission checks. Claude Code will be able to execute any shell command, read/write any file, and make network requests without asking.
- `IS_SANDBOX=1` tricks the root-user check so the flag is accepted even under `root`.
- This is intended for trusted environments (personal machines, containers, CI). Do NOT recommend this for shared or production systems.
