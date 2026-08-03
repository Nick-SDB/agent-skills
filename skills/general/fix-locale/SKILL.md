---
name: fix-locale
description: Diagnose and fix UTF-8 locale problems that corrupt CJK or other non-ASCII text. Use when characters render as boxes, underscores, question marks, or mojibake.
---

# Fix UTF-8 Locale Problems

Diagnose before modifying configuration. Use the locale requested by the user; otherwise prefer an installed UTF-8 locale appropriate to the system instead of assuming a language.

## Diagnose

1. Run `locale`, inspect `LANG`, `LC_CTYPE`, and `LC_ALL`, and list installed locales with `locale -a` when available.
2. Check whether the session runs inside tmux by inspecting `TMUX`.
3. Inspect the active shell and its user startup files.
4. Distinguish configuration problems from terminal font or encoding problems.

Treat empty values, `C`, `POSIX`, or a non-UTF-8 locale as likely causes. Check whether locale exports appear after an early return in a shell startup file.

## Repair user configuration

1. Select a locale that appears in `locale -a`.
2. Preserve existing content and avoid duplicate exports.
3. Put required exports before any non-interactive early return:

```bash
export LANG=<installed-utf8-locale>
export LC_ALL=<installed-utf8-locale>
```

Set `LANGUAGE` only on systems that support it and only when a language preference is known.

## Repair system configuration when required

Request authorization before editing system files or generating locales. Use the operating system's supported locale configuration mechanism. On Debian-derived systems this may include `locale-gen`; on RHEL-derived systems it may include `localedef`.

Do not write a locale that the system has not generated.

## Verify

1. Start a fresh shell and rerun `locale`.
2. Print representative ASCII and non-ASCII text.
3. If tmux was active, restart the tmux server or verify outside tmux; existing servers retain their original environment.
4. Report the root cause, files changed, commands run, and any verification that still requires a new terminal session.

Do not claim success solely because a startup file was edited.
