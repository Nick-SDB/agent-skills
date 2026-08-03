---
name: install-openspec
description: Install and initialize OpenSpec for one or more coding agents. Use when setting up spec-driven development in a project or verifying an OpenSpec installation.
---

# Install OpenSpec

Install OpenSpec only after confirming the requested scope and target agents.

## Check prerequisites

1. Confirm Node.js meets OpenSpec's current minimum version.
2. Detect the user's preferred package manager.
3. Check whether `openspec` is already installed and report its version.

## Install

Use the preferred package manager, for example:

```bash
npm install -g @fission-ai/openspec@latest
```

Offer a no-global-install alternative when appropriate:

```bash
npx @fission-ai/openspec@latest init
```

Verify a global installation with `openspec --version`.

## Initialize

1. Confirm the project root.
2. Determine the target agent identifiers from the request and installed tools; do not default silently to one vendor.
3. Run `openspec init --tools <comma-separated-targets>` when targets are known, or `openspec init` for interactive selection.
4. Preserve existing OpenSpec configuration and stop for confirmation before replacing conflicting files.
5. Report created files and the next OpenSpec command to run.

Consult the current OpenSpec help output when target identifiers or prerequisites differ from these examples.
