---
name: fix-locale
description: Detect and fix UTF-8/locale issues causing Chinese/Japanese characters to display as underscores or question marks. Use when user reports characters not rendering correctly.
argument-hint: "[locale]"
allowed-tools: Bash Grep Read Write Edit Glob
---

# Fix UTF-8 Locale Issues

Detect and fix locale/UTF-8 encoding issues that cause CJK (Chinese, Japanese, Korean) characters to display incorrectly (as underscores, boxes, or question marks).

## Current System State

```
Current locale: !`locale 2>/dev/null || echo "locale command not found"`
LANG variable: !`echo $LANG`
TMUX session: !`echo "TMUX=$TMUX"`
```

## Important: Check for tmux

If `TMUX=$TMUX` shows a value (not empty), the session is running inside tmux. **Locale changes made to ~/.bashrc may not apply inside tmux** because tmux spawns a new session that does not source ~/.bashrc.

If running inside tmux:
- Tell the user: "You appear to be running inside tmux. Locale changes to ~/.bashrc won't apply inside the current tmux session. Please exit tmux completely, then source ~/.bashrc in a fresh terminal to apply the changes."
- Do NOT say the fix is working if the user is in tmux - the verification should be done outside tmux.

## Step 1: Check for Locale Problems

1. Run `locale` to see all LC_* variables
2. Run `echo $LANG` to check LANG setting
3. If any of these show problems:
   - Empty LANG
   - LC_CTYPE="POSIX" or "C"
   - Missing UTF-8 in the locale string

## Step 2: Detect Common Issues

- **Issue A**: LANG not set or empty
- **Issue B**: Locale set but not exported in shell config
- **Issue C**: Locale set after early-return in .bashrc (never executes)
- **Issue D**: System locale not configured (/etc/default/locale)
- **Issue E**: Locale not generated on the system

## Step 3: Fix the Issues

### Fix A & B: Set locale in ~/.bashrc

Read the user's `.bashrc` (check $HOME/.bashrc or /root/.bashrc):

```bash
# Find the bashrc
bashrc_path="$HOME/.bashrc"
if [ ! -f "$bashrc_path" ]; then
  bashrc_path="/root/.bashrc"
fi
```

Add these lines **at the very top** (before any `[ -z "$PS1" ] && return` line):

```bash
# Set locale for UTF-8 support (must be before interactive check)
export LANG=zh_CN.UTF-8
export LANGUAGE=zh_CN:zh:en_US:en
export LC_ALL=zh_CN.UTF-8
```

If user specified a different locale in $ARGUMENTS, use that instead (e.g., `ja_JP.UTF-8` for Japanese).

### Fix C: Ensure locale is before early-return

The lines MUST appear before:
```bash
[ -z "$PS1" ] && return
```

If they appear after, move them to the top.

### Fix D: Set system locale

Write to `/etc/default/locale`:
```
LANG=zh_CN.UTF-8
LANGUAGE=zh_CN:zh:en_US:en
LC_ALL=zh_CN.UTF-8
```

### Fix E: Generate locale if needed

If locale `zh_CN.UTF-8` is not generated, run:
```bash
locale-gen zh_CN.UTF-8
```

Or on RHEL/CentOS:
```bash
localedef -i zh_CN -f UTF-8 zh_CN.UTF-8
```

## Step 4: Verify the Fix

After making changes, run:
```bash
source ~/.bashrc
locale
echo "中文测试 Chinese test 日本語"
```

All CJK characters should render correctly.

**Note**: If you are inside tmux, exit tmux first and verify in a fresh terminal outside tmux. The locale changes to ~/.bashrc may not apply to existing tmux sessions.

## Output Summary

Report to the user:
1. What was wrong (which issues were detected)
2. What files were modified
3. Verification results showing characters now render correctly

**Important**: Do NOT confidently say the fix is "working" or "complete". Instead:
- Say something like "The configuration has been updated. Please verify in a new terminal session."
- If in tmux, explicitly warn that verification must be done outside tmux
- Remind the user that they may need to restart their terminal or tmux session for changes to take effect