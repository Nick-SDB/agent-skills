---
name: remote-shell-safe-exec
description: Execute multi-line shell workflows over SSH, including commands inside Docker or Podman containers, without fragile nested quoting. Use when a task involves ssh plus sh/bash -lc, heredocs, JSON, curl payloads, shell variables, command substitutions, secrets, or two or more shell-parsing layers; also use when a prior remote command failed with unexpected token, bad substitution, missing delimiter, or quote-related syntax errors.
---

# Remote Shell Safe Exec

Send a complete script over standard input and let exactly one remote shell parse it. Avoid compressing a multi-line program into an `ssh host "... sh -lc '...'"` string.

## Workflow

1. Identify every parser in the path: tool-call language, local shell, SSH remote command, container CLI, remote shell, and application parser such as JSON or SQL.
2. Keep the SSH command fixed and short. Transmit the variable program through stdin.
3. Use a single-quoted heredoc delimiter so the local shell does not expand `$`, backticks, backslashes, or command substitutions.
4. Parse the transmitted script once with `bash -s` or `sh -s` at the final execution layer.
5. Validate syntax before execution when practical, then preserve and report the actual exit status.

## Preferred patterns

Run on the remote host:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes host \
  'exec /bin/bash -s' <<'REMOTE_SCRIPT'
set -euo pipefail
printf '%s\n' "$SOME_REMOTE_VARIABLE"
REMOTE_SCRIPT
```

Run inside an existing container without nesting `sh -lc`:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes host \
  'exec docker exec -i container-name /bin/bash -s' <<'CONTAINER_SCRIPT'
set -euo pipefail
payload='{"model":"example","stream":false}'
printf '%s\n' "$payload"
CONTAINER_SCRIPT
```

Prefer the bundled wrapper when the target fits its constraints:

```bash
/path/to/remote-shell-safe-exec/scripts/run_remote_script.sh host <<'REMOTE_SCRIPT'
set -euo pipefail
hostname
REMOTE_SCRIPT

/path/to/remote-shell-safe-exec/scripts/run_remote_script.sh \
  --container container-name host <<'CONTAINER_SCRIPT'
set -euo pipefail
date -Is
CONTAINER_SCRIPT
```

The wrapper accepts only a host, an optional validated container name, a final shell choice, and a connection timeout. Put all task arguments inside the stdin script instead of adding another quoting layer.

## Rules for interpolation

- Treat the heredoc body as remote code. Use `<<'NAME'`, not `<<NAME`, unless local interpolation is explicitly required.
- If a local value must cross the boundary, prefer a validated positional value encoded for the target format. Never concatenate untrusted text into remote code.
- Do not use `eval`.
- Do not use base64 merely to hide quoting mistakes. Use it only for genuinely binary payloads and validate both encoder and decoder.
- If the tool-call language uses template literals, remember that it may process `${...}` before any shell runs. Escape that syntax or avoid template literals.
- Quote application data for its own parser. Shell quoting does not make JSON, YAML, SQL, or regex syntax valid.

## Secrets

- Never place tokens, passwords, or authorization headers in the SSH remote-command string, process arguments, diagnostics, or shell tracing.
- Load existing credentials at the final execution layer when authorized, for example by sourcing a protected remote environment file.
- Feed sensitive curl headers through stdin with `curl --config -`; do not use `curl -H "Authorization: Bearer $TOKEN"`, because arguments can be visible in process listings.
- Keep `set -x` disabled around secrets. Print status, timing, response shape, and byte counts instead of response bodies when proving connectivity.

Example:

```bash
set -a
. /protected/profile.env
set +a
{
  printf 'header = "Authorization: Bearer %s"\n' "$API_KEY"
  printf 'header = "Content-Type: application/json"\n'
} | curl --config - --silent --show-error --connect-timeout 10 --max-time 45 \
  --data-binary "$payload" 'https://example.invalid/v1/chat/completions'
```

## Validation and failure classification

- Extract the script locally and run `bash -n` or `sh -n` when its syntax is non-trivial. Syntax checking does not authorize executing its commands.
- Use explicit SSH, connection, and total-operation timeouts. Keep `BatchMode=yes` for unattended work and stop on authentication or host-key failures.
- A failure before the remote script's first marker is usually a tool/local quoting failure. A remote `bash: syntax error` is a transmitted-script failure. An application timeout or HTTP error is a workload result.
- Do not reinterpret a wrapper/parser failure as evidence about the remote service.
- Avoid automatic retries for commands with side effects. Retry only after proving the first attempt did not reach the mutation point.
- Preserve the user's authorization boundaries. This skill fixes transport and parsing; it does not grant permission to mutate remote state.

## Avoid

```bash
# Fragile: several parsers compete for the same quotes and substitutions.
ssh host "docker exec app sh -lc 'R=$(curl -d '{\"x\":\"$VALUE\"}' URL); echo $R'"
```

Replace it with a fixed SSH/container command plus a quoted heredoc body.
