---
name: deploy-dsh
description: Deploy, upgrade, migrate, validate, or troubleshoot DeepSeek Harness (dsh) on local or remote Linux hosts and containers. Use for reproducible DSH runtime installation, provider wiring, service lifecycle, private remote access, rollback, and deployment failures; do not use for a purely conceptual project introduction.
---

# Deploy DSH

Deploy a reproducible DSH instance without overwriting unrelated user state or widening network access.

## Establish scope first

Distinguish planning, read-only diagnosis, installation, upgrade, and removal. A request to explain or plan does not authorize changes. Installation authority covers normal target-host files and processes, but not host firewall rules, container recreation, `authorized_keys`, credential copying, public port exposure, or turning another machine into a proxy unless the user explicitly includes that work.

Treat existing sessions, settings, credentials, source trees, package stores, services, and unrelated worktree changes as user-owned. Preserve them. Do not copy `auth.json`, API keys, DSH credentials, settings, or sessions between hosts by default.

## Discover before choosing an install mode

Run read-only checks for:

- effective user, groups, OS, architecture, Node/npm/Corepack/pnpm, existing DSH and provider versions;
- target filesystem, free space, ownership, persistent mounts, and whether the target is a container;
- PID 1, system/user systemd availability, D-Bus and `XDG_RUNTIME_DIR`, current tmux or supervisor processes;
- requested port, current listeners, shared-user/network-namespace exposure, SSH reachability and egress/proxy health;
- Codex binary/version and authentication-file metadata when a Codex provider is requested. Never print credential contents.

Run [scripts/preflight.sh](scripts/preflight.sh) with Bash locally on the target, or inspect the same facts directly. Read [references/container-networking.md](references/container-networking.md) when PID 1 is not systemd, the target is containerized, or host port publishing is discussed.

## Choose the least expansive reproducible installation

- For ordinary installation, use an isolated user-owned runtime and an exact DSH version with a lockfile.
- Use `npx @deepseek-ai/dsh web` only for disposable evaluation unless the user prefers it; it does not provide the same release and rollback control.
- Use source builds only for DSH development, a source patch, or when the user explicitly requests them.
- If registry access is unusable, prefer verified package archives or a lockfile-backed runtime transfer from a compatible host. Verify OS, architecture, Node ABI, archive hashes, and native imports before activation.

Read [references/deployment-workflow.md](references/deployment-workflow.md) for installation, upgrade, offline transfer, activation, verification, cleanup, and rollback details.

## Keep runtime, state, and credentials separate

Use a configurable layout with versioned releases and an atomic `current` link. Put runtime and DSH state on a persistent, user-owned filesystem when the target is ephemeral. Keep `DSH_HOME` separate from the runtime. Initialize a fresh profile, then copy or adapt only explicitly selected provider/preset configuration.

Use exact package versions and verified provider artifacts. Do not silently substitute “latest,” mix release candidates, or rebuild a previously verified custom provider on the target. Query current versions only when requested or needed, because DSH is a developer-preview project and package behavior can change.

## Select lifecycle and access mechanisms from observed facts

- Use a user systemd service only when a user manager is actually reachable and suitable for restart persistence.
- In a container without systemd, use an existing supervisor/orchestrator when available. A tmux plus `flock` launcher is acceptable for an explicitly non-persistent or interim service, but state that it does not survive container recreation.
- Bind the Web UI to loopback and use an SSH local forward by default. Loopback is not an authorization boundary against users in the same network namespace.
- Do not publish the Web UI to a LAN or public interface without a separately approved authentication and network-control design.

## Handle Codex providers as a separate compatibility surface

Read [references/codex-provider.md](references/codex-provider.md) whenever native Codex, Codex OAuth/subscriptions, `auth.json`, `CODEX_HOME`, `app-server`, or a Codex subagent is involved. Verify the installed DSH provider README and the installed Codex protocol version instead of assuming compatibility from package names.

## Verify before declaring success

Verify the inactive release first, then activate it and verify the assembled service:

- exact DSH/provider versions and artifact hashes;
- lockfile closure and native/provider imports;
- profile composition with no load errors;
- one service instance, expected owner, loopback-only listener, HTTP success, and access through the intended SSH tunnel;
- native provider authentication and a minimal real request when credentials and network access are in scope;
- the DSH provider path with a bounded scratch task, cleanup, and no orphan child process;
- rollback path and disk usage.

Run [scripts/verify.sh](scripts/verify.sh) with Bash for common read-only invariants. Report partial success precisely: distinguish installation, authentication, provider handshake, and upstream network/model completion. Do not call a deployment fully usable when a required real request failed.

Clean only temporary files created by the deployment after the replacement has passed verification. Resolve destructive targets first, keep them inside the deployment root, and explain what was removed and how it can be recreated.
