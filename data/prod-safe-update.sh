#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'

PROJECT_DIR="/home/deploy/vpn-stack"
VPN_MODE="preserve"
BRANCH="${BRANCH:-main}"
REMOTE="${REMOTE:-origin}"
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/vpn-stack-backups}"
STOP_TIMEOUT="${STOP_TIMEOUT:-30}"
START_TIMEOUT="${START_TIMEOUT:-180}"
STABILITY_SECONDS="${STABILITY_SECONDS:-15}"
XRAY_INTERNAL_PORT="${XRAY_INTERNAL_PORT:-8443}"
XRAY_TARGET="${XRAY_TARGET:-www.google.com:443}"
XRAY_SERVER_NAME="${XRAY_SERVER_NAME:-www.google.com}"

usage() {
  cat <<'EOF'
Usage: vpn-stack-safe-update.sh [OPTIONS] [PROJECT_DIR]

Options:
  --preserve-vpn  Preserve all VPN keys, peers and handshake parameters (default).
  --reset-vpn     Generate a completely new VPN configuration. Clients must be
                  reconfigured after this operation.
  -h, --help      Show this help.

The foreground launcher verifies/adds the UFW rule for the target Xray public
port (8443/tcp by default) before starting the detached update. Existing rules,
including 443/tcp, are retained for rollback.
EOF
}

while (($#)); do
  case "$1" in
    --preserve-vpn)
      VPN_MODE="preserve"
      ;;
    --reset-vpn)
      VPN_MODE="reset"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      printf 'Unknown option: %s\n' "$1" >&2
      usage >&2
      exit 64
      ;;
    *)
      if [[ "$PROJECT_DIR" != "/home/deploy/vpn-stack" ]]; then
        printf 'Only one PROJECT_DIR may be specified.\n' >&2
        exit 64
      fi
      PROJECT_DIR="$1"
      ;;
  esac
  shift
done

env_value() {
  local key="$1"
  local env_file="$PROJECT_DIR/.env"
  [[ -f "$env_file" ]] || return 1
  awk -F '=' -v key="$key" '$1 == key { sub(/^[^=]*=/, ""); print; exit }' "$env_file"
}

XRAY_PUBLIC_PORT="${XRAY_PUBLIC_PORT:-8443}"
[[ "$XRAY_PUBLIC_PORT" =~ ^[0-9]+$ ]] &&
  (( XRAY_PUBLIC_PORT >= 1 && XRAY_PUBLIC_PORT <= 65535 )) || {
  printf 'Invalid target Xray public port: %s\n' "$XRAY_PUBLIC_PORT" >&2
  exit 64
}

script_path="$(readlink -f "$0")"
timestamp="${VPN_UPDATE_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
backup_dir="$BACKUP_ROOT/$timestamp"
log_file="$backup_dir/update.log"
image_map="$backup_dir/images.tsv"
backup_ready=0
rollback_running=0
stack_interrupted=0

if [[ "${VPN_UPDATE_DETACHED:-0}" != "1" ]]; then
  if [[ -f /etc/ufw/ufw.conf ]] &&
    grep -Eq '^ENABLED=(yes|YES|true|TRUE|1)$' /etc/ufw/ufw.conf; then
    command -v sudo >/dev/null 2>&1 || {
      printf 'UFW is enabled, but sudo is unavailable.\n' >&2
      exit 1
    }
    printf 'Checking UFW rule for Xray public port %s/tcp.\n' "$XRAY_PUBLIC_PORT"
    sudo -v
    sudo ufw allow "$XRAY_PUBLIC_PORT/tcp"
    sudo ufw status | grep -Eq "(^|[[:space:]])${XRAY_PUBLIC_PORT}/tcp([[:space:]]|$)" || {
      printf 'UFW does not report an allow rule for %s/tcp.\n' "$XRAY_PUBLIC_PORT" >&2
      exit 1
    }
  fi

  mkdir -p "$backup_dir"
  chmod 700 "$BACKUP_ROOT" "$backup_dir"
  launcher_log="$backup_dir/launcher.log"

  nohup env \
    VPN_UPDATE_DETACHED=1 \
    VPN_UPDATE_RUN_ID="$timestamp" \
    BRANCH="$BRANCH" \
    REMOTE="$REMOTE" \
    BACKUP_ROOT="$BACKUP_ROOT" \
    STOP_TIMEOUT="$STOP_TIMEOUT" \
    START_TIMEOUT="$START_TIMEOUT" \
    STABILITY_SECONDS="$STABILITY_SECONDS" \
    XRAY_INTERNAL_PORT="$XRAY_INTERNAL_PORT" \
    XRAY_PUBLIC_PORT="$XRAY_PUBLIC_PORT" \
    XRAY_TARGET="$XRAY_TARGET" \
    XRAY_SERVER_NAME="$XRAY_SERVER_NAME" \
    bash "$script_path" "--${VPN_MODE}-vpn" "$PROJECT_DIR" \
    > "$launcher_log" 2>&1 < /dev/null &

  child_pid=$!
  printf 'Update started in background (PID %s).\n' "$child_pid"
  printf 'Live log: %s\n' "$launcher_log"
  printf 'Monitor: tail -f %q\n' "$launcher_log"
  exit 0
fi

log() {
  printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*" | tee -a "$log_file"
}

die() {
  log "ERROR: $*"
  return 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "Required command is missing: $1"
}

compose() {
  docker compose --project-directory "$PROJECT_DIR" -f "$PROJECT_DIR/docker-compose.yml" "$@"
}

service_container() {
  compose ps -q "$1"
}

archive_project_as_root() {
  docker run --rm \
    --entrypoint tar \
    -v "$PROJECT_DIR:/project:ro" \
    "$runtime_helper_image" \
    --exclude='./.git' -C /project -cpf - . \
    > "$backup_dir/project.tar"
}

extract_project_as_root() {
  docker run --rm -i \
    --entrypoint tar \
    -v "$PROJECT_DIR:/project" \
    "$runtime_helper_image" \
    -C /project -xpf - \
    < "$backup_dir/project.tar"
}

extract_wg_runtime_as_root() {
  docker run --rm -i \
    --entrypoint tar \
    -v "$PROJECT_DIR:/project" \
    "$runtime_helper_image" \
    -C /project -xpf - ./data/wg-easy \
    < "$backup_dir/project.tar"
}

copy_wg_json_as_root() {
  docker run --rm \
    --entrypoint cat \
    -v "$PROJECT_DIR/data/wg-easy:/wireguard:ro" \
    "$runtime_helper_image" \
    /wireguard/wg0.json \
    > "$1"
}

compare_wg_json_as_root() {
  docker run --rm \
    --entrypoint cmp \
    -v "$PROJECT_DIR/data/wg-easy:/wireguard:ro" \
    -v "$backup_dir:/backup:ro" \
    "$runtime_helper_image" \
    -s /backup/wg0.preserved.json /wireguard/wg0.json
}

copy_xray_config_as_root() {
  docker run --rm \
    --entrypoint cat \
    -v "$PROJECT_DIR/xray-config:/xray:ro" \
    "$runtime_helper_image" \
    /xray/config.json \
    > "$1"
}

install_xray_config_as_root() {
  docker run --rm \
    --entrypoint sh \
    -v "$PROJECT_DIR/xray-config:/xray" \
    -v "$backup_dir:/backup:ro" \
    "$runtime_helper_image" \
    -c 'cat /backup/xray.migrated.json > /xray/config.json && chmod 600 /xray/config.json'
}

set_env_value() {
  local key="$1"
  local value="$2"
  local env_file="$PROJECT_DIR/.env"

  [[ -f "$env_file" ]] || die "Environment file is missing: $env_file"
  python3 - "$env_file" "$key" "$value" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]
lines = path.read_text(encoding="utf-8").splitlines()
replacement = f"{key}={value}"
found = False
result = []

for line in lines:
    if line.split("=", 1)[0] == key:
        if not found:
            result.append(replacement)
            found = True
        continue
    result.append(line)

if not found:
    result.append(replacement)

path.write_text("\n".join(result) + "\n", encoding="utf-8")
PY
}

prepare_xray_state() {
  local config_path="$PROJECT_DIR/xray-config/config.json"
  local candidate_path="$backup_dir/xray.migrated.json"

  copy_xray_config_as_root "$backup_dir/xray.preserved.json"
  [[ -s "$backup_dir/xray.preserved.json" ]] ||
    die "Cannot preserve Xray state: $config_path is missing or empty"
  chmod 600 "$backup_dir/xray.preserved.json"
  cp -p "$backup_dir/xray.preserved.json" "$candidate_path"

  python3 - \
    "$candidate_path" \
    "$XRAY_INTERNAL_PORT" \
    "$XRAY_TARGET" \
    "$XRAY_SERVER_NAME" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
internal_port = int(sys.argv[2])
target = sys.argv[3]
server_name = sys.argv[4]
config = json.loads(path.read_text(encoding="utf-8"))

matches = []
for inbound in config.get("inbounds", []):
    stream = inbound.get("streamSettings", {})
    if inbound.get("protocol") == "vless" and stream.get("security") == "reality":
        matches.append((inbound, stream.get("realitySettings", {})))

if len(matches) != 1:
    raise SystemExit(f"expected exactly one VLESS Reality inbound, found {len(matches)}")

inbound, reality = matches[0]
clients = inbound.get("settings", {}).get("clients")
private_key = reality.get("privateKey")
short_ids = reality.get("shortIds")

if not isinstance(clients, list) or not clients:
    raise SystemExit("VLESS Reality clients are missing")
if not isinstance(private_key, str) or not private_key:
    raise SystemExit("Reality privateKey is missing")
if not isinstance(short_ids, list) or not short_ids:
    raise SystemExit("Reality shortIds are missing")

inbound["listen"] = "0.0.0.0"
inbound["port"] = internal_port
reality.pop("dest", None)
reality["target"] = target
reality["serverNames"] = [server_name]
path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
PY

  install_xray_config_as_root
  set_env_value XRAY_PORT "$XRAY_PUBLIC_PORT"
  set_env_value XRAY_SERVER_NAME "$XRAY_SERVER_NAME"
  log "Xray migration prepared: ${XRAY_PUBLIC_PORT}/tcp -> ${XRAY_INTERNAL_PORT}/tcp, target $XRAY_TARGET"
}

validate_xray_config() {
  local config_path="$PROJECT_DIR/xray-config/config.json"
  local xray_image

  xray_image="$(compose config --images | awk '/teddysun\/xray/ { print; exit }')"
  [[ -n "$xray_image" ]] || die "Cannot determine the Xray image from Compose"

  docker run --rm \
    --entrypoint xray \
    -v "$config_path:/config.json:ro" \
    "$xray_image" \
    run -test -config /config.json |
    tee -a "$log_file"
}

verify_xray_runtime() {
  local id runtime_config inbound_port public_port binding

  id="$(service_container xray)"
  [[ -n "$id" ]] || {
    die "No container found for service xray"
    return 1
  }
  runtime_config="$backup_dir/xray.runtime.json"

  docker exec "$id" xray run -test -config /etc/xray/config.json |
    tee -a "$log_file" || return 1
  docker exec "$id" cat /etc/xray/config.json > "$runtime_config" || {
    die "Cannot read the active Xray config"
    return 1
  }
  chmod 600 "$runtime_config"

  inbound_port="$(python3 - "$runtime_config" <<'PY'
import json
import sys

config = json.load(open(sys.argv[1], encoding="utf-8"))
matches = [
    inbound for inbound in config.get("inbounds", [])
    if inbound.get("protocol") == "vless"
    and inbound.get("streamSettings", {}).get("security") == "reality"
]
if len(matches) != 1:
    raise SystemExit(1)
print(matches[0]["port"])
PY
  )" || {
    die "Cannot determine the active Xray inbound port"
    return 1
  }
  public_port="$(env_value XRAY_PORT || true)"
  public_port="${public_port:-$inbound_port}"

  binding="$(docker port "$id" "${inbound_port}/tcp" 2>/dev/null || true)"
  [[ "$binding" == *":${public_port}"* ]] || {
    die "Xray port binding is incorrect: expected ${public_port}->${inbound_port}, got ${binding:-none}"
    return 1
  }

  python3 - "$public_port" <<'PY' || {
import socket
import sys

port = int(sys.argv[1])
with socket.create_connection(("127.0.0.1", port), timeout=5):
    pass
PY
    die "Xray TCP port $public_port is not reachable locally"
    return 1
  }
  log "Xray config is valid and TCP port $public_port is reachable locally"
}

verify_xray_migration() {
  local current_path="$backup_dir/xray.current.json"

  copy_xray_config_as_root "$current_path"
  chmod 600 "$current_path"
  python3 - \
    "$current_path" \
    "$backup_dir/xray.preserved.json" \
    "$XRAY_INTERNAL_PORT" \
    "$XRAY_TARGET" \
    "$XRAY_SERVER_NAME" <<'PY'
import json
import sys

current_path, previous_path = sys.argv[1:3]
expected_port = int(sys.argv[3])
expected_target = sys.argv[4]
expected_server_name = sys.argv[5]

current = json.load(open(current_path, encoding="utf-8"))
previous = json.load(open(previous_path, encoding="utf-8"))

def reality_inbound(config):
    matches = [
        inbound for inbound in config.get("inbounds", [])
        if inbound.get("protocol") == "vless"
        and inbound.get("streamSettings", {}).get("security") == "reality"
    ]
    if len(matches) != 1:
        raise SystemExit(f"expected one VLESS Reality inbound, found {len(matches)}")
    inbound = matches[0]
    return inbound, inbound["streamSettings"]["realitySettings"]

current_inbound, current_reality = reality_inbound(current)
previous_inbound, previous_reality = reality_inbound(previous)

if current_inbound.get("port") != expected_port:
    raise SystemExit("Xray inbound port migration was not applied")
if current_reality.get("target") != expected_target:
    raise SystemExit("Xray Reality target migration was not applied")
if current_reality.get("serverNames") != [expected_server_name]:
    raise SystemExit("Xray Reality serverNames migration was not applied")
if "dest" in current_reality:
    raise SystemExit("Legacy Xray Reality dest field is still present")

if current_inbound.get("settings", {}).get("clients") != previous_inbound.get("settings", {}).get("clients"):
    raise SystemExit("Xray clients changed during migration")
if current_reality.get("privateKey") != previous_reality.get("privateKey"):
    raise SystemExit("Xray privateKey changed during migration")
if current_reality.get("shortIds") != previous_reality.get("shortIds"):
    raise SystemExit("Xray shortIds changed during migration")
PY
  log "Xray clients, private key and short IDs are preserved"
}

wait_until_stopped() {
  local deadline=$((SECONDS + STOP_TIMEOUT))
  local ids id running

  while (( SECONDS < deadline )); do
    ids="$(compose ps -aq)"
    running=0
    while IFS= read -r id; do
      [[ -z "$id" ]] && continue
      if [[ "$(docker inspect -f '{{.State.Running}}' "$id")" == "true" ]]; then
        running=1
        break
      fi
    done <<< "$ids"
    (( running == 0 )) && return 0
    sleep 1
  done

  die "Some project containers are still running after ${STOP_TIMEOUT}s"
}

wait_until_healthy() {
  local deadline=$((SECONDS + START_TIMEOUT))
  local services service id state health all_ready

  services="$(compose config --services)"
  while (( SECONDS < deadline )); do
    all_ready=1
    while IFS= read -r service; do
      [[ -z "$service" ]] && continue
      id="$(service_container "$service")"
      if [[ -z "$id" ]]; then
        all_ready=0
        continue
      fi

      state="$(docker inspect -f '{{.State.Status}}' "$id")"
      health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$id")"
      if [[ "$state" != "running" || "$health" == "unhealthy" || "$health" == "starting" ]]; then
        all_ready=0
      fi
    done <<< "$services"

    (( all_ready == 1 )) && return 0
    sleep 2
  done

  compose logs --no-color --tail 300 > "$backup_dir/readiness-timeout.log" 2>&1 || true
  compose ps -a | tee -a "$log_file"
  die "The stack did not become ready within ${START_TIMEOUT}s"
}

verify_stack() {
  local services service id state health restart_before restart_after
  local check_started

  wait_until_healthy
  services="$(compose config --services)"
  check_started="$(date -u +%FT%TZ)"
  : > "$backup_dir/verification.tsv"

  while IFS= read -r service; do
    [[ -z "$service" ]] && continue
    id="$(service_container "$service")"
    [[ -n "$id" ]] || die "No container found for service $service"

    state="$(docker inspect -f '{{.State.Status}}' "$id")"
    health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$id")"
    restart_before="$(docker inspect -f '{{.RestartCount}}' "$id")"

    [[ "$state" == "running" ]] || die "$service is not running: $state"
    [[ "$health" == "none" || "$health" == "healthy" ]] ||
      die "$service health is $health"
    [[ "$(docker inspect -f '{{.State.OOMKilled}}' "$id")" == "false" ]] ||
      die "$service was OOM-killed"

    printf '%s\t%s\t%s\t%s\n' "$service" "$id" "$health" "$restart_before" \
      >> "$backup_dir/verification.tsv"
  done <<< "$services"

  docker exec "$(service_container wg-easy)" /usr/bin/wg show >/dev/null ||
    die "wg-easy cannot read the WireGuard interface"
  verify_xray_runtime

  sleep "$STABILITY_SECONDS"

  while IFS= read -r service; do
    [[ -z "$service" ]] && continue
    id="$(service_container "$service")"
    state="$(docker inspect -f '{{.State.Status}}' "$id")"
    restart_after="$(docker inspect -f '{{.RestartCount}}' "$id")"
    restart_before="$(awk -F '\t' -v name="$service" '$1 == name { print $4 }' "$backup_dir/verification.tsv")"

    [[ "$state" == "running" ]] || die "$service stopped during the stability check"
    [[ "$restart_after" == "$restart_before" ]] ||
      die "$service restarted during the stability check"
  done <<< "$services"

  if compose logs --no-color --since "$check_started" |
    grep -Eai '(^|[^a-z])(fatal|panic|traceback|exception|error)([^a-z]|$)' \
    > "$backup_dir/error-lines.log"; then
    cat "$backup_dir/error-lines.log" | tee -a "$log_file"
    die "Error markers were found in fresh container logs"
  fi

  compose ps -a | tee -a "$log_file"
  log "All services are running and stable"
}

restore_runtime_data() {
  if tar -tf "$backup_dir/project.tar" |
    grep '^\./data/wg-easy/' > "$backup_dir/wg-runtime-files.txt"; then
    extract_wg_runtime_as_root
  else
    die "The project backup does not contain data/wg-easy runtime files"
  fi
}

prepare_vpn_state() {
  case "$VPN_MODE" in
    preserve)
      restore_runtime_data
      [[ -f "$PROJECT_DIR/data/wg-easy/wg0.json" ]] ||
        die "Cannot preserve VPN state: data/wg-easy/wg0.json is missing"
      copy_wg_json_as_root "$backup_dir/wg0.preserved.json"
      chmod 600 "$backup_dir/wg0.preserved.json"
      log "VPN mode: preserve existing keys, peers and handshake parameters"
      ;;
    reset)
      log "WARNING: VPN mode is reset; new server/client keys and parameters will be generated"
      rm -f "$PROJECT_DIR/data/wg-easy/wg0.json" "$PROJECT_DIR/data/wg-easy/wg0.conf"
      ;;
    *)
      die "Unsupported VPN mode: $VPN_MODE"
      ;;
  esac
}

verify_vpn_state() {
  local current_config="$PROJECT_DIR/data/wg-easy/wg0.json"

  [[ -s "$current_config" ]] || die "VPN configuration was not generated"

  if [[ "$VPN_MODE" == "preserve" ]] &&
    ! compare_wg_json_as_root; then
    copy_wg_json_as_root "$backup_dir/wg0.changed.json"
    chmod 600 "$backup_dir/wg0.changed.json"
    die "wg0.json changed in preserve mode; refusing the update"
  fi

  if [[ "$VPN_MODE" == "preserve" ]]; then
    log "VPN keys, peers and saved handshake parameters are unchanged"
  else
    log "A new VPN configuration was generated as explicitly requested"
  fi
}

final_report() {
  local outcome="$1"
  local detail="${2:-}"
  local services service id state health restart_count
  local service_count=0
  local running_count=0
  local total_restarts=0
  local wg_health="unknown"
  local wg_peers="unknown"
  local wg_match="no"
  local xray_valid="no"
  local xray_port="unknown"
  local xray_target="unknown"
  local checked_ports=""
  local port port_result

  services="$(compose config --services 2>/dev/null || true)"
  while IFS= read -r service; do
    [[ -z "$service" ]] && continue
    service_count=$((service_count + 1))
    id="$(service_container "$service" 2>/dev/null || true)"
    [[ -n "$id" ]] || continue
    state="$(docker inspect -f '{{.State.Status}}' "$id" 2>/dev/null || true)"
    health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$id" 2>/dev/null || true)"
    restart_count="$(docker inspect -f '{{.RestartCount}}' "$id" 2>/dev/null || printf '0')"
    [[ "$state" == "running" ]] && running_count=$((running_count + 1))
    [[ "$restart_count" =~ ^[0-9]+$ ]] &&
      total_restarts=$((total_restarts + restart_count))
    if [[ "$service" == "wg-easy" ]]; then
      wg_health="$health"
    fi
  done <<< "$services"

  wg_peers="$(
    docker exec "$(service_container wg-easy 2>/dev/null)" \
      sh -c 'wg show wg0 peers | wc -w' 2>/dev/null || printf 'unknown'
  )"

  if [[ -f "$backup_dir/project.tar" ]]; then
    local backup_conf_hash backup_json_hash active_conf_hash active_json_hash
    backup_conf_hash="$(
      tar -xOf "$backup_dir/project.tar" ./data/wg-easy/wg0.conf 2>/dev/null |
        sha256sum | awk '{print $1}'
    )"
    backup_json_hash="$(
      tar -xOf "$backup_dir/project.tar" ./data/wg-easy/wg0.json 2>/dev/null |
        sha256sum | awk '{print $1}'
    )"
    active_conf_hash="$(
      docker run --rm \
        --entrypoint cat \
        -v "$PROJECT_DIR/data/wg-easy:/wireguard:ro" \
        "$runtime_helper_image" \
        /wireguard/wg0.conf 2>/dev/null |
        sha256sum | awk '{print $1}'
    )"
    active_json_hash="$(
      docker run --rm \
        --entrypoint cat \
        -v "$PROJECT_DIR/data/wg-easy:/wireguard:ro" \
        "$runtime_helper_image" \
        /wireguard/wg0.json 2>/dev/null |
        sha256sum | awk '{print $1}'
    )"
    if [[ -n "$backup_conf_hash" && -n "$backup_json_hash" &&
      "$backup_conf_hash" == "$active_conf_hash" &&
      "$backup_json_hash" == "$active_json_hash" ]]; then
      wg_match="yes"
    fi
  fi

  id="$(service_container xray 2>/dev/null || true)"
  if [[ -n "$id" ]] &&
    docker exec "$id" xray run -test -config /etc/xray/config.json >/dev/null 2>&1; then
    xray_valid="yes"
  fi

  local report_xray_config="$backup_dir/xray.report.json"
  if [[ -n "$id" ]]; then
    docker exec "$id" cat /etc/xray/config.json > "$report_xray_config" 2>/dev/null || true
    chmod 600 "$report_xray_config" 2>/dev/null || true
  fi
  IFS=$'\t' read -r xray_port xray_target < <(
    python3 - "$report_xray_config" <<'PY' 2>/dev/null || true
import json
import sys

config = json.load(open(sys.argv[1], encoding="utf-8"))
for inbound in config.get("inbounds", []):
    stream = inbound.get("streamSettings", {})
    if inbound.get("protocol") == "vless" and stream.get("security") == "reality":
        reality = stream.get("realitySettings", {})
        target = reality.get("target") or reality.get("dest") or "unknown"
        print(f"{inbound.get('port', 'unknown')}\t{target}")
        break
PY
  ) || true
  xray_port="$(env_value XRAY_PORT 2>/dev/null || printf '%s' "$xray_port")"

  for port in "$xray_port" 51821; do
    [[ "$port" =~ ^[0-9]+$ ]] || continue
    port_result="$(
      python3 - "$port" <<'PY' 2>/dev/null
import socket
import sys

with socket.create_connection(("127.0.0.1", int(sys.argv[1])), timeout=3):
    pass
PY
      if [[ $? -eq 0 ]]; then printf 'ok'; else printf 'failed'; fi
    )"
    if [[ -n "$checked_ports" ]]; then
      checked_ports+=", "
    fi
    checked_ports+="${port}/tcp=${port_result}"
  done

  {
    printf '\nРабота скрипта завершена: %s\n' "$outcome"
    [[ -n "$detail" ]] && printf '  Причина/результат: %s\n' "$detail"
    printf '  - контейнеры: %s из %s работают, суммарных рестартов %s;\n' \
      "$running_count" "$service_count" "$total_restarts"
    printf '  - wg-easy health: %s;\n' "$wg_health"
    printf '  - WireGuard peers: %s;\n' "$wg_peers"
    if [[ "$wg_match" == "yes" ]]; then
      printf '  - WG-файлы побайтово совпадают с backup;\n'
    else
      printf '  - ВНИМАНИЕ: WG-файлы не совпадают с backup или сравнение не выполнено;\n'
    fi
    printf '  - Xray config: %s;\n' "$([[ "$xray_valid" == "yes" ]] && printf 'валиден' || printf 'НЕ ПРОШЕЛ ПРОВЕРКУ')"
    printf '  - локальные TCP-порты: %s;\n' "${checked_ports:-не проверены}"
    printf '  - текущий Xray: порт %s, Reality target %s;\n' "$xray_port" "$xray_target"
    printf '  - Git commit: %s;\n' "$(git -C "$PROJECT_DIR" rev-parse --short HEAD 2>/dev/null || printf 'unknown')"
    printf '  - backup: %s.\n\n' "$backup_dir"
  } | tee -a "$log_file" "$backup_dir/final-report.txt"
  chmod 600 "$backup_dir/final-report.txt" 2>/dev/null || true

  return 0
}

rollback() {
  local reason="${1:-unknown failure}"
  local service image_id original_ref backup_ref

  (( backup_ready == 1 )) || return 0
  (( rollback_running == 0 )) || return 0
  rollback_running=1
  trap - ERR INT TERM
  set +e

  log "ROLLBACK: $reason"
  if (( stack_interrupted == 1 )); then
    compose down --remove-orphans --timeout "$STOP_TIMEOUT" >> "$log_file" 2>&1
  fi

  git -C "$PROJECT_DIR" reset --hard "$old_head" >> "$log_file" 2>&1
  extract_project_as_root >> "$log_file" 2>&1
  docker load -i "$backup_dir/images.tar" >> "$log_file" 2>&1

  while IFS=$'\t' read -r service image_id original_ref backup_ref; do
    [[ -n "$original_ref" ]] || continue
    docker image tag "$backup_ref" "$original_ref" >> "$log_file" 2>&1
  done < "$image_map"

  if (( stack_interrupted == 0 )); then
    if compose config -q >> "$log_file" 2>&1 && verify_stack; then
      log "ROLLBACK COMPLETE: preparation failed before downtime; the previous stack kept running"
      log "Backup retained at: $backup_dir"
      final_report \
        "обновление не применено, предыдущий стек продолжил работу" \
        "$reason"
      exit 1
    fi
  elif compose config -q >> "$log_file" 2>&1 &&
    compose up -d --force-recreate --no-build >> "$log_file" 2>&1 &&
    verify_stack; then
    log "ROLLBACK COMPLETE: the previous stack is running"
    log "Backup retained at: $backup_dir"
    final_report \
      "обновление не применено, выполнен автоматический откат" \
      "$reason"
    exit 1
  fi

  log "CRITICAL: automatic rollback failed"
  log "Backup retained at: $backup_dir"
  compose ps -a | tee -a "$log_file"
  final_report \
    "КРИТИЧЕСКАЯ ОШИБКА: автоматический откат не завершён" \
    "$reason"
  exit 2
}

on_error() {
  local exit_code=$?
  local line_no="${1:-unknown}"
  rollback "command failed at line $line_no with exit code $exit_code"
  exit "$exit_code"
}

if [[ "${VPN_UPDATE_REPORT_ONLY:-0}" == "1" ]]; then
  backup_dir="${REPORT_BACKUP_DIR:?REPORT_BACKUP_DIR is required}"
  log_file="$backup_dir/update.log"
  runtime_helper_image="$(docker inspect -f '{{.Image}}' "$(service_container wg-easy)")"
  final_report \
    "${REPORT_OUTCOME:-диагностический отчёт}" \
    "${REPORT_DETAIL:-проверка формата финального отчёта}"
  exit 0
fi

mkdir -p "$backup_dir"
chmod 700 "$BACKUP_ROOT" "$backup_dir"
touch "$log_file"
chmod 600 "$log_file"
trap 'on_error $LINENO' ERR
trap 'rollback "received an interrupt or termination signal"' INT TERM

require_command docker
require_command git
require_command tar
require_command grep
require_command awk
require_command cmp
require_command python3

[[ -d "$PROJECT_DIR/.git" ]] || die "Not a git repository: $PROJECT_DIR"
[[ -f "$PROJECT_DIR/docker-compose.yml" ]] || die "docker-compose.yml is missing"
docker info >/dev/null
compose version >/dev/null
compose config -q

exec 9>"$BACKUP_ROOT/update.lock"
if command -v flock >/dev/null 2>&1; then
  flock -n 9 || die "Another update process is already running"
fi

old_head="$(git -C "$PROJECT_DIR" rev-parse HEAD)"
runtime_helper_image="$(docker inspect -f '{{.Image}}' "$(service_container wg-easy)")"
[[ -n "$runtime_helper_image" ]] || die "Cannot determine the runtime backup helper image"
log "Project: $PROJECT_DIR"
log "Current commit: $old_head"
log "Requested VPN mode: $VPN_MODE"
log "Requested Xray migration: ${XRAY_PUBLIC_PORT}/tcp -> ${XRAY_INTERNAL_PORT}/tcp, target $XRAY_TARGET"
git -C "$PROJECT_DIR" status --short | tee "$backup_dir/git-status.txt" | tee -a "$log_file"
git -C "$PROJECT_DIR" diff -- \
  . \
  ':(exclude)data/wg-easy/wg0.conf' \
  ':(exclude)data/wg-easy/wg0.json' \
  > "$backup_dir/working-tree.patch"
git -C "$PROJECT_DIR" diff --cached > "$backup_dir/index.patch"
git -C "$PROJECT_DIR" bundle create "$backup_dir/repository.bundle" --all
archive_project_as_root

services="$(compose config --services)"
backup_refs=()
while IFS= read -r service; do
  [[ -z "$service" ]] && continue
  id="$(service_container "$service")"
  [[ -n "$id" ]] || die "Service $service has no existing container to back up"
  [[ "$(docker inspect -f '{{.State.Running}}' "$id")" == "true" ]] ||
    die "Existing service $service is not running"

  image_id="$(docker inspect -f '{{.Image}}' "$id")"
  original_ref="$(docker inspect -f '{{.Config.Image}}' "$id")"
  backup_ref="vpn-stack-backup/${service}:${timestamp}"
  docker image tag "$image_id" "$backup_ref"
  backup_refs+=("$backup_ref")
  printf '%s\t%s\t%s\t%s\n' "$service" "$image_id" "$original_ref" "$backup_ref" >> "$image_map"
done <<< "$services"

docker image save -o "$backup_dir/images.tar" "${backup_refs[@]}"
docker inspect $(compose ps -aq) > "$backup_dir/containers.json"
compose config > "$backup_dir/compose.resolved.yml"
compose logs --no-color --tail 500 > "$backup_dir/logs-before-update.txt"
chmod 600 "$backup_dir"/*
backup_ready=1
log "Backup complete: $backup_dir"

log "Fetching $REMOTE/$BRANCH"
git -C "$PROJECT_DIR" fetch --prune "$REMOTE" "$BRANCH"
new_head="$(git -C "$PROJECT_DIR" rev-parse "$REMOTE/$BRANCH")"
git -C "$PROJECT_DIR" reset --hard "$new_head"
prepare_vpn_state
prepare_xray_state
compose config -q
log "Source updated to: $new_head"

log "Pulling external images and rebuilding local images before downtime"
compose pull --ignore-buildable
DOCKER_COMPOSE_EXPERIMENTAL=false compose build --pull
validate_xray_config
verify_xray_migration
log "Preparation and validation completed while the old stack remained running"

log "Stopping the current stack"
stack_interrupted=1
compose stop --timeout "$STOP_TIMEOUT"
wait_until_stopped
log "All project containers are stopped"

log "Starting the updated stack"
compose up -d --force-recreate
verify_stack
verify_vpn_state
verify_xray_migration

trap - ERR INT TERM
log "UPDATE COMPLETE: $old_head -> $new_head"
log "Backup retained at: $backup_dir"
final_report \
  "обновление успешно применено" \
  "$old_head -> $new_head"
