---
name: tmux-mouse-scroll
description: Enable mouse wheel scrolling in tmux sessions. Use when the user wants to scroll with the mouse in tmux, enable tmux mouse mode, or fix mouse scrolling not working in tmux.
disable-model-invocation: true
---

# Enable Mouse Wheel Scrolling in tmux

Set up tmux so the mouse wheel scrolls through terminal history, and mouse clicks can select panes/windows.

## What to do

1. Check if `~/.tmux.conf` exists and whether `set -g mouse on` is already present.
2. If already configured, tell the user it's already set up. If in a live tmux session, suggest reloading with `tmux source-file ~/.tmux.conf`.
3. If not configured, append `set -g mouse on` to `~/.tmux.conf` (create the file if needed).
4. If the user is currently inside a tmux session (check `$TMUX` env var), run `tmux source-file ~/.tmux.conf` to apply immediately.
5. If not in a tmux session, tell the user it will take effect next time they start tmux, or they can run `tmux source-file ~/.tmux.conf` from within a tmux session.

## What `set -g mouse on` does

- **Scroll**: mouse wheel scrolls through scrollback buffer (enters copy mode automatically)
- **Pane select**: click a pane to focus it
- **Pane resize**: drag pane borders to resize
- **Window select**: click window names in the status bar

This single setting replaces the old tmux < 2.1 options (`mouse-select-pane`, `mouse-resize-pane`, `mouse-select-window`, `mouse-utf8`).

## Troubleshooting tips

If scrolling still doesn't work after enabling:

- **Terminal emulator**: make sure your terminal sends mouse events (most modern terminals do by default — iTerm2, Alacritty, Windows Terminal, GNOME Terminal all work)
- **Nested SSH**: if you're SSH'd into a remote machine running tmux, the local terminal must forward mouse events through SSH (usually automatic)
- **tmux version**: `set -g mouse on` requires tmux >= 2.1. Check with `tmux -V`
- **Reload config**: changes to `.tmux.conf` don't auto-apply to running sessions — reload with `tmux source-file ~/.tmux.conf` or `Ctrl-b` then `:source-file ~/.tmux.conf`
- **Copy mode conflict**: while scrolling, tmux enters copy mode. Press `q` to exit copy mode and return to normal
