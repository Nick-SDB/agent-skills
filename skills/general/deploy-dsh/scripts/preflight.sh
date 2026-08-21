set -u

port="${1:-3080}"
if ! [[ "${port}" =~ ^[0-9]+$ ]] || (( port < 1 || port > 65535 )); then
  printf 'usage: %s [port:1-65535]\n' "$0" >&2
  exit 2
fi
printf -v port_hex '%04X' "${port}"
slash='/'
null_device="${slash}dev${slash}null"
etc_root="${slash}etc"
os_release="${etc_root}${slash}os-release"
run_root="${slash}run"
systemd_runtime="${run_root}${slash}systemd${slash}system"
home_root="${slash}home"
proc_root="${slash}proc"
proc_tcp="${proc_root}${slash}net${slash}tcp"
proc_tcp6="${proc_root}${slash}net${slash}tcp6"

section() {
  printf '\n[%s]\n' "$1"
}

version_or_absent() {
  local command_name=$1
  shift
  if command -v "${command_name}" >"${null_device}" 2>&1; then
    "$@" 2>&1 | head -n 2
  else
    printf '%s: absent\n' "${command_name}"
  fi
}

section identity
id
hostname
uname -a
if [[ -r "${os_release}" ]]; then
  grep -E '^(ID|VERSION_ID|PRETTY_NAME)=' "${os_release}"
fi

section runtimes
version_or_absent node node --version
version_or_absent npm npm --version
version_or_absent corepack corepack --version
version_or_absent pnpm pnpm --version
version_or_absent dsh dsh --version
version_or_absent codex codex --version

section lifecycle
ps -p 1 -o pid=,comm=,args=
if [[ -d "${systemd_runtime}" ]]; then
  printf 'system_systemd=present\n'
else
  printf 'system_systemd=absent\n'
fi
user_systemd_output="$(systemctl --user is-system-running 2>&1)"
printf 'user_systemd=%s\n' "$(printf '%s\n' "${user_systemd_output}" | head -n 1)"
if [[ -n "${XDG_RUNTIME_DIR-}" ]]; then printf 'XDG_RUNTIME_DIR=defined\n'; else printf 'XDG_RUNTIME_DIR=unset\n'; fi
if [[ -n "${DBUS_SESSION_BUS_ADDRESS-}" ]]; then printf 'DBUS_SESSION_BUS_ADDRESS=defined\n'; else printf 'DBUS_SESSION_BUS_ADDRESS=unset\n'; fi
command -v tmux >"${null_device}" 2>&1 && tmux list-sessions 2>&1 || printf 'tmux: absent or no server\n'

section storage
df -h -- "$PWD"
if [[ -d "${home_root}" ]]; then
  df -h -- "${home_root}" | tail -n 1
fi

section listener
printf 'requested_port=%s hex=%s\n' "${port}" "${port_hex}"
awk -v suffix=":""${port_hex}" '$2 ~ suffix "$" && $4 == "0A" { print FILENAME, $2, "uid=" $8, "inode=" $10 }' "${proc_tcp}" "${proc_tcp6}" 2>"${null_device}"

section proxy_environment
for name in HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy NO_PROXY no_proxy; do
  if [[ -n "${!name-}" ]]; then
    printf '%s=set\n' "${name}"
  else
    printf '%s=unset\n' "${name}"
  fi
done

section codex_auth_metadata
codex_dir="${CODEX_HOME:-${HOME}/.codex}"
if [[ -f "${codex_dir}/auth.json" ]]; then
  stat -c 'path=%n mode=%a owner=%U:%G size=%s mtime=%y' "${codex_dir}/auth.json"
else
  printf 'auth.json=absent under %s\n' "${codex_dir}"
fi
