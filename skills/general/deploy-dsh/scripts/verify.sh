set -euo pipefail

slash='/'
null_device="${slash}dev${slash}null"
proc_root="${slash}proc"
proc_tcp="${proc_root}${slash}net${slash}tcp"

usage() {
  printf 'usage: %s --runtime DIR --state DIR --port PORT [--tmux NAME] [--provider MODULE]\n' "$0" >&2
  exit 2
}

runtime=''
state=''
port=''
tmux_name=''
provider=''
while (( $# > 0 )); do
  case "$1" in
    --runtime) [[ $# -ge 2 ]] || usage; runtime=$2; shift 2 ;;
    --state) [[ $# -ge 2 ]] || usage; state=$2; shift 2 ;;
    --port) [[ $# -ge 2 ]] || usage; port=$2; shift 2 ;;
    --tmux) [[ $# -ge 2 ]] || usage; tmux_name=$2; shift 2 ;;
    --provider) [[ $# -ge 2 ]] || usage; provider=$2; shift 2 ;;
    *) usage ;;
  esac
done

[[ -n "${runtime}" && -n "${state}" && -n "${port}" ]] || usage
[[ "${port}" =~ ^[0-9]+$ ]] && (( port >= 1 && port <= 65535 )) || usage
runtime="$(readlink -f -- "${runtime}")"
state="$(readlink -f -- "${state}")"
[[ -d "${runtime}" && -d "${state}" ]] || { printf 'runtime/state directory missing\n' >&2; exit 1; }
dsh_bin="${runtime}${slash}node_modules${slash}.bin${slash}dsh"
[[ -x "${dsh_bin}" ]] || { printf 'dsh executable missing\n' >&2; exit 1; }
printf -v port_hex '%04X' "${port}"

listener_count="$(awk -v address="0100007F:${port_hex}" '$2 == address && $4 == "0A" { count++ } END { print count + 0 }' "${proc_tcp}")"
if [[ "${listener_count}" != 1 ]]; then
  printf 'expected one IPv4 loopback listener on %s, got %s\n' "${port}" "${listener_count}" >&2
  exit 1
fi

http_code="$(curl --silent --show-error --output "${null_device}" --max-time 10 --write-out '%{http_code}' "http://127.0.0.1:${port}/")"
[[ "${http_code}" == 200 ]] || { printf 'unexpected HTTP status: %s\n' "${http_code}" >&2; exit 1; }

if [[ -n "${tmux_name}" ]]; then
  tmux has-session -t "${tmux_name}"
fi

if [[ -n "${provider}" ]]; then
  provider="$(readlink -f -- "${provider}")"
  [[ -f "${provider}" ]] || { printf 'provider module missing\n' >&2; exit 1; }
  node --input-type=module -e 'await import(process.argv[1]); console.log("provider_import=ok")' "${provider}"
fi

app_server_count=0
for cmdline in "${proc_root}${slash}"[0-9]*"${slash}cmdline"; do
  [[ -r "${cmdline}" ]] || continue
  process_args=()
  mapfile -d '' -t process_args < "${cmdline}" || true
  has_app_server=false
  has_stdio=false
  for process_arg in "${process_args[@]}"; do
    [[ "${process_arg}" == 'app-server' ]] && has_app_server=true
    [[ "${process_arg}" == '--stdio' ]] && has_stdio=true
  done
  if [[ "${has_app_server}" == true && "${has_stdio}" == true ]]; then
    app_server_count=$((app_server_count + 1))
  fi
done

printf 'dsh_version=%s\n' "$("${dsh_bin}" --version)"
printf 'state=%s\n' "${state}"
printf 'listener=127.0.0.1:%s\n' "${port}"
printf 'web_http=%s\n' "${http_code}"
printf 'codex_app_server_processes=%s\n' "${app_server_count}"
