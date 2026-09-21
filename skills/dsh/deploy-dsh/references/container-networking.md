# Containers, lifecycle, and private access

Read this reference when the target may be a container, PID 1 is not systemd, or the user asks about host port forwarding.

## Determine the actual boundary

Strong container indicators include PID 1 being `sshd` or an application process, the systemd runtime marker being absent, `loginctl` reporting that systemd is not PID 1, a container-style address, and no system D-Bus/logind. The presence of a `systemd` binary does not mean a system or user manager is running.

`systemctl --user` requires a reachable user manager and user D-Bus. Missing `XDG_RUNTIME_DIR`, a missing per-user runtime directory, and no logind commonly explain `offline`. Do not “fix” this by exporting guessed variables: a path and bus address do not create a manager.

Use the container platform or existing supervisor for restart persistence. Adding systemd to an existing container usually requires changing its image/entrypoint, cgroup setup, privileges, and orchestration; that is a separate infrastructure change.

## SSH tunnel usually needs no published Web port

If SSH already reaches `sshd` inside the container, a client-side local forward can terminate at container loopback:

```text
browser -> client 127.0.0.1:<local-port>
        -> existing SSH connection
        -> container 127.0.0.1:<dsh-port>
```

Example:

```sh
ssh -N -L <local-port>:127.0.0.1:<dsh-port> <container-ssh-alias>
```

No Docker/Kubernetes publication of the DSH port is needed for this path. This is usually the preferred private-access design.

## Direct host publication is a different design

Container port publication normally connects to the container's network address, not its loopback. A service bound only to container `127.0.0.1` therefore cannot usually be reached by `host-port -> container-port` DNAT. Direct publication generally requires either:

- DSH listening on the container interface (`0.0.0.0`) while the host publishes only on host `127.0.0.1`; or
- a deliberately configured in-container/sidecar proxy from the container interface to DSH loopback.

Existing Docker containers usually need recreation to add published ports. Kubernetes usually needs a Service, port-forward, or workload change. These actions require container-host or orchestrator authority.

Never bind both container and host publicly by accident. DSH loopback alone does not authenticate users in the same network namespace, and a host-loopback mapping still requires SSH or another approved path for remote access.

## Persistence

Confirm that runtime and `DSH_HOME` are on a persistent bind mount or volume before relying on them across container recreation. A persisted filesystem does not persist tmux, locks, sockets, or processes; the external supervisor must launch the service again.
