---
name: cc-skip-permissions
description: Configure a clearly named Claude Code launcher that bypasses interactive permission prompts. Use only for explicitly requested automation in trusted disposable or isolated environments.
---

# Configure a No-Prompt Claude Code Launcher

Warn that `--dangerously-skip-permissions` permits unrestricted command execution, file access, and network requests. Require explicit confirmation before changing shell configuration. Do not recommend this mode on shared machines or production hosts.

## Configure

1. Determine the requested shell from the task or current environment.
2. Select its user configuration file:
   - Bash: `~/.bashrc`
   - Zsh: `~/.zshrc`
   - Fish: `~/.config/fish/config.fish`
3. Inspect the file and avoid duplicate definitions.
4. Add a separate alias so the ordinary `claude` command remains safe:

```bash
alias claude-unrestricted='IS_SANDBOX=1 claude --dangerously-skip-permissions'
```

For Fish, use:

```fish
alias claude-unrestricted 'IS_SANDBOX=1 claude --dangerously-skip-permissions'
```

5. Reload the configuration only when doing so cannot disrupt the current session; otherwise tell the user how to reload it.
6. Report the exact file and line added.

Never weaken existing project or organization permission policy. If Claude Code rejects the flag, report the rejection instead of attempting additional bypasses.
