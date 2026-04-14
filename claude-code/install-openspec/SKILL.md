---
name: install-openspec
description: Install and initialize OpenSpec (spec-driven development framework for AI coding assistants). Use when the user wants to set up OpenSpec in a project or install it globally.
disable-model-invocation: true
argument-hint: "[--tools claude,cursor,...]"
---

# Install OpenSpec

OpenSpec is a spec-driven development (SDD) framework by Fission-AI that helps AI coding assistants and developers agree on requirements before writing code.

- **Repo**: https://github.com/Fission-AI/OpenSpec
- **Site**: https://openspec.dev/

## Prerequisites

- Node.js >= v20.19.0

Check if Node.js is installed and meets the version requirement. If not, tell the user to install or upgrade Node.js first.

## Steps

### 1. Install OpenSpec globally

Try the user's preferred package manager in this order of preference (check which is available):

```bash
npm install -g @fission-ai/openspec@latest
# or
pnpm add -g @fission-ai/openspec@latest
# or
yarn global add @fission-ai/openspec@latest
# or
bun add -g @fission-ai/openspec@latest
```

Verify installation with `openspec --version`.

### 2. Initialize in the current project

```bash
openspec init
```

If $ARGUMENTS is provided (e.g. `--tools claude,cursor`), pass it along:

```bash
openspec init $ARGUMENTS
```

If no arguments given, default to Claude Code:

```bash
openspec init --tools claude
```

This creates the `.openspec/` directory with spec files and configures tool-specific settings.

### 3. Supported tools

If the user asks which tools are supported, the full list is:

`amazon-q`, `antigravity`, `auggie`, `bob`, `claude`, `cline`, `codex`, `codebuddy`, `continue`, `costrict`, `crush`, `cursor`, `factory`, `forgecode`, `gemini`, `github-copilot`, `iflow`, `junie`, `kilocode`, `kiro`, `opencode`, `pi`, `qoder`, `qwen`, `roocode`, `trae`, `windsurf`

Multiple tools can be specified: `openspec init --tools claude,cursor,windsurf`

## Quick usage (without global install)

If the user prefers not to install globally:

```bash
npx @fission-ai/openspec@latest init --tools claude
```
