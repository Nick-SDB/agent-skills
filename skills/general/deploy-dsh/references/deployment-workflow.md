# DSH deployment workflow

Use this reference for an installation, upgrade, migration, or rollback. Replace example variables and ports with discovered values; no example path is authorization to modify that location.

## 1. Define the deployment

Record:

- target SSH identity or local host;
- requested DSH version and any provider artifact/version;
- persistent deployment root, state root, working directory, bind address, port, and access method;
- lifecycle owner: user systemd, container supervisor, external orchestrator, or interim tmux;
- credential source and whether a real paid/model request is authorized.

If the user asks for “latest,” resolve it from the current official repository or package registry and report the exact selected version before mutation. Otherwise preserve the requested or already validated version.

## 2. Prefer a release layout

A useful layout is:

```text
<deploy-root>/
  artifacts/
  releases/<exact-version>/
  current -> releases/<exact-version>
  bin/
  logs/
  run/
<state-root>/
```

Keep directories private (`0700`) and ordinary config files private (`0600`) unless a component requires another mode. Avoid system-global npm installs when a user-owned runtime is sufficient.

The release manifest should use exact direct dependency versions. Include a lockfile. If a provider is a local tarball, prefer a path relative to the release or deployment root so the lockfile is portable. Allow dependency build scripts only for packages the chosen release requires and whose role has been reviewed.

Install the inactive release, run `dsh --version`, load provider and native modules, and inspect the direct package list before changing `current`.

## 3. Registry and offline modes

### Registry-backed install

Use the available package manager through Corepack or a user-owned installation. Keep the package-manager version explicit when reproducing another deployment. A frozen lockfile failure is evidence to investigate, not permission to discard the lockfile or float versions.

### Verified artifact transfer

When egress is broken but a known-good host exists:

1. Compare architecture, OS/libc, Node version/ABI, package-manager format, and provider/Codex protocol versions.
2. Transfer the smallest sufficient artifacts through an approved path such as `scp -3`.
3. Compute SHA-256 at source and destination.
4. Prefer a fresh target install from a transferred package store or archive. Copy a complete `node_modules` runtime only when platforms match and native modules will be explicitly imported on the target.
5. Preserve an incomplete target install by renaming it until the replacement passes; clean it afterward.

Do not treat a successful `dsh --version` as proof that all native modules work. Import the provider and native subprocess/terminal modules, then boot the assembled profile on an ephemeral loopback port.

## 4. Initialize state and configuration

Set a fresh `DSH_HOME` and start the Web profile once on `127.0.0.1` with an ephemeral port and `--no-open`. Stop it cleanly after profile files are generated.

Apply only the required patch entries and presets. Avoid copying another deployment's credentials, user settings, sessions, anonymous identifier, workspace database, or caches. If configuration must be migrated, enumerate the exact files, inspect for secrets, and obtain the user's authorization for credential movement.

When a provider module is optional, mount it once on the host plane and expose its tool only in the intended preset. Resolve the module from the active runtime rather than a source checkout. Validate the full profile after patching.

## 5. Activate and run

After inactive verification, create or switch `current` atomically. Do not overwrite an unrelated existing launcher. A launcher should set the intended `PATH`, `DSH_HOME`, ordinary home variables needed by providers, and a single-instance lock before executing:

```text
dsh web --host <bind-address> --port <port> --no-open
```

For user systemd, use an absolute executable, explicit environment, restart-on-failure, and a working directory that exists. Confirm `systemctl --user` talks to a real user manager before installing a unit.

For an interim tmux service, use a uniquely named session, redirect logs inside the private deployment root, and use `flock` so duplicate sessions cannot create duplicate servers. State clearly that tmux is not reboot or container-recreation persistence.

## 6. Verify and roll back

Verification should cover inactive artifacts, assembled configuration, live process, listener, HTTP, intended remote access, credentials, and one bounded provider request. Inspect logs after each real request and ensure child process trees terminate.

Rollback should stop only the deployment's process, point `current` to the previous verified release, and restart using the same lifecycle mechanism. Do not delete the failed release until rollback and diagnosis are complete. Keep state-format compatibility in mind: developer-preview releases may not read each other's state, so back up state before an upgrade and do not assume downgrade compatibility.

After success, delete only known temporary archives and incomplete directories inside the resolved deployment root. Keep the provider artifact and previous release when they are part of the intended rollback story and disk space permits.
