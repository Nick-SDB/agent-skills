#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: run_remote_script.sh [--container NAME] [--shell bash|sh] [--connect-timeout SECONDS] HOST

Read a shell script from stdin and execute it with one final shell on HOST.
When --container is supplied, execute the script inside that existing Docker container.
USAGE
}

container=''
shell_name='bash'
connect_timeout='10'

while (($#)); do
  case "$1" in
    --container)
      (($# >= 2)) || { usage; exit 64; }
      container=$2
      shift 2
      ;;
    --shell)
      (($# >= 2)) || { usage; exit 64; }
      shell_name=$2
      shift 2
      ;;
    --connect-timeout)
      (($# >= 2)) || { usage; exit 64; }
      connect_timeout=$2
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      printf 'Unknown option: %s\n' "$1" >&2
      usage
      exit 64
      ;;
    *)
      break
      ;;
  esac
done

(($# == 1)) || { usage; exit 64; }
host=$1

[[ $host =~ ^[A-Za-z0-9_.@-]+$ ]] || {
  printf 'Unsafe host value: %s\n' "$host" >&2
  exit 64
}
[[ $connect_timeout =~ ^[1-9][0-9]*$ ]] || {
  printf 'Connect timeout must be a positive integer.\n' >&2
  exit 64
}

case "$shell_name" in
  bash) shell_path='/bin/bash' ;;
  sh) shell_path='/bin/sh' ;;
  *)
    printf 'Shell must be bash or sh.\n' >&2
    exit 64
    ;;
esac

if [[ -n $container ]]; then
  [[ $container =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || {
    printf 'Unsafe container name: %s\n' "$container" >&2
    exit 64
  }
  remote_command="exec docker exec -i $container $shell_path -s"
else
  remote_command="exec $shell_path -s"
fi

exec ssh \
  -o BatchMode=yes \
  -o ConnectTimeout="$connect_timeout" \
  -o StrictHostKeyChecking=yes \
  -o ServerAliveInterval=15 \
  -o ServerAliveCountMax=2 \
  -- "$host" "$remote_command"
