# Codex provider deployment

Read this reference whenever DSH will use a native Codex CLI, Codex subscription/OAuth state, `auth.json`, `CODEX_HOME`, `app-server`, or a Codex subagent.

## Distinguish two provider roles

Do not assume one “Codex provider” covers both roles:

1. A DSH main-LLM adapter streams the parent agent's model requests.
2. A native Codex subagent provider spawns `codex app-server --stdio` for delegated work.

Inspect the installed package READMEs and configuration catalog for the exact DSH version. Some DSH/pi-ai releases deliberately do not support OAuth-only providers as main-LLM routes, even though a native Codex subagent can use the host's Codex login. A Codex subscription being usable by the CLI is not proof that the parent DSH model route can consume it.

## Native provider prerequisites

Verify:

- `codex` resolves through the service's `PATH`;
- the installed Codex CLI/app-server version matches the provider's tested protocol baseline;
- provider thread settings such as approval policy and sandbox match the intended unattended authority;
- the provider starts a fresh process per run or otherwise has documented credential refresh behavior.

Do not install Codex, log in, choose a model, or overwrite `CODEX_HOME` merely because the optional DSH provider is installed. Those remain host/account decisions unless the user asks for them.

## Authentication handling

Prefer the target host's existing login. Never display or copy `auth.json` by default. Check only metadata such as existence, owner, mode, size, and modification time.

When the provider supports an environment overlay, explicitly set ordinary location variables when deterministic resolution is required:

```text
HOME=<target-user-home>
CODEX_HOME=<target-user-codex-directory>
```

Point to the directory, not a frozen copy of the credential file. Verify from current Codex documentation and installed CLI help that the selected version honors the variable. Do not pass credential contents through command-line arguments, logs, patches, or world-readable environment files.

If authentication changes after DSH starts, determine whether the provider starts a new app-server for each run or caches a long-lived process. Test the observed behavior; do not assume a restart is or is not required.

## Layered validation

Use a bounded scratch directory and test in this order:

1. Codex version and app-server help/handshake without a paid request when possible.
2. A native ephemeral Codex request with read-only sandbox and an exact short response.
3. A direct DSH subagent-registry request that creates one harmless sentinel file inside the scratch workspace and returns a sentinel response.
4. The assembled Web preset/tool path, if the parent model route is configured.

Apply a finite timeout, capture non-secret logs, dispose the run, and compare the `codex app-server --stdio` process set before and after the test so unrelated active runs are not labeled as orphans. Remove only the scratch directory created by the test.

Interpret failures by layer:

- failure before spawn: package/configuration or provider registration;
- app-server handshake/protocol error: version incompatibility;
- model/account recognized but HTTP request fails: egress, proxy, DNS, TLS, or upstream availability;
- 401/refresh failure: authentication state;
- parent agent unavailable while native subagent works: main-LLM route limitation or missing parent credentials.

Test configured proxy and direct egress separately without printing proxy credentials. Do not add SSH keys, open firewall rules, publish a proxy, or route traffic through another host without explicit approval.
