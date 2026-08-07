---
name: configure-codex-http-only
description: Configure Codex CLI or Desktop to use the Responses API over HTTP/SSE instead of WebSocket while retaining ChatGPT/OpenAI authentication. Use when Codex repeatedly shows Reconnecting, stream disconnected, TLS or proxy-related WebSocket failures, when a proxy does not reliably support WebSocket upgrades, or when applying the same HTTP-only configuration on another machine.
---

# Configure Codex HTTP Only

Apply a reversible user-level Codex configuration that selects a custom provider with WebSocket support disabled. Preserve the user's model and unrelated settings.

## Workflow

1. Confirm that `codex` is installed and identify the user config path. Use `$CODEX_HOME/config.toml` when `CODEX_HOME` is set; otherwise use `~/.codex/config.toml`.
2. Run the bundled script in check mode:

   ```bash
   python3 scripts/configure_http_only.py --check
   ```

3. If the user asked only for diagnosis, report the check result and stop. If the user asked to configure or fix the machine, run:

   ```bash
   python3 scripts/configure_http_only.py
   ```

   Pass `--config /absolute/path/to/config.toml` only for a non-default config location.

4. Run `codex doctor --json` and confirm:
   - `config.load` is `ok`.
   - The active model provider is `openai_http`.
   - Provider reachability succeeds or returns an actionable network error.
5. Tell the user to fully quit and reopen Codex Desktop, or restart the CLI session. Existing processes do not reload `config.toml` automatically.

## Configuration Contract

The script must produce these effective values:

```toml
model_provider = "openai_http"

[model_providers.openai_http]
name = "OpenAI HTTP Only"
wire_api = "responses"
supports_websockets = false
requires_openai_auth = true
```

`wire_api = "responses"` selects the Responses API; it does not by itself disable WebSocket. `supports_websockets = false` is the transport switch.

## Safety

- Always preserve unrelated settings and comments.
- Always create a timestamped backup before changing an existing file.
- Treat repeated execution as idempotent; do not create a backup when no change is needed.
- Stop if the existing `openai_http` provider uses another authentication mechanism such as `env_key`, `experimental_bearer_token`, or a nested `auth` table. Do not overwrite an ambiguous provider.
- Do not change the selected model, authentication files, proxy application, or system network settings unless the user separately requests it.
- Explain that HTTP-only transport cannot repair a failed DNS or TLS connection. If `codex doctor` still reports reachability failures, diagnose the proxy or network separately.

## Resources

- `scripts/configure_http_only.py`: inspect, back up, atomically update, and validate the Codex TOML configuration.
