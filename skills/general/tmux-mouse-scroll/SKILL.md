---
name: tmux-mouse-scroll
description: Enable and troubleshoot mouse scrolling in tmux. Use when mouse-wheel scrollback, pane selection, resizing, or status-bar clicking does not work.
---

# Enable Mouse Scrolling in tmux

1. Check `tmux -V`; require tmux 2.1 or newer for the unified mouse setting.
2. Inspect `~/.tmux.conf` for an existing mouse configuration.
3. Add the following line only when it is absent:

```tmux
set -g mouse on
```

4. If a tmux server is running, reload the file with `tmux source-file ~/.tmux.conf` after confirming the path.
5. Otherwise explain that the setting takes effect when tmux next starts.

This setting enables wheel scrollback, pane selection, pane resizing, and status-bar window selection.

If scrolling still fails, check terminal mouse-event support, nested SSH behavior, copy mode, the loaded configuration path, and conflicting later settings. Press `q` to leave copy mode after scrolling.
