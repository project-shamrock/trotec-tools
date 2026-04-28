#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$SCRIPT_DIR/tunnel.config.json"
PID_DIR="$SCRIPT_DIR/.pids"
mkdir -p "$PID_DIR"

HOST=$(jq -r '.host' "$CONFIG")

usage() {
  echo "Usage: tunnel.sh <command> [tunnel-name]"
  echo ""
  echo "Commands:"
  echo "  up [name]      Open tunnel (or all tunnels if no name given)"
  echo "  down [name]    Close tunnel (or all tunnels)"
  echo "  status         Show status of all tunnels"
  echo "  list           List available tunnel configs"
  echo "  ssh            Open interactive SSH session to the host"
  echo "  exec <cmd>     Run a command on the remote host"
  echo "  test [name]    Test connectivity through tunnels"
  echo ""
  echo "Tunnels are defined in tunnel.config.json"
}

get_tunnel_names() {
  jq -r '.tunnels | keys[]' "$CONFIG"
}

get_tunnel_field() {
  local name="$1" field="$2"
  jq -r ".tunnels[\"$name\"].$field" "$CONFIG"
}

pid_file() {
  echo "$PID_DIR/$1.pid"
}

is_running() {
  local pf
  pf=$(pid_file "$1")
  [[ -f "$pf" ]] && kill -0 "$(cat "$pf")" 2>/dev/null
}

tunnel_up() {
  local name="$1"
  if is_running "$name"; then
    echo "[$name] already running (pid $(cat "$(pid_file "$name")"))"
    return
  fi

  local lport rport desc
  lport=$(get_tunnel_field "$name" "localPort")
  rport=$(get_tunnel_field "$name" "remotePort")
  desc=$(get_tunnel_field "$name" "description")

  echo "[$name] opening tunnel: localhost:$lport -> $HOST:$rport ($desc)"
  ssh -f -N -L "$lport:127.0.0.1:$rport" "$HOST"

  # find the ssh pid
  local pid
  pid=$(pgrep -f "ssh.*-L.*$lport:127.0.0.1:$rport.*$HOST" | tail -1)
  if [[ -n "$pid" ]]; then
    echo "$pid" > "$(pid_file "$name")"
    echo "[$name] tunnel up (pid $pid)"
  else
    echo "[$name] WARNING: tunnel started but could not find pid"
  fi
}

tunnel_down() {
  local name="$1"
  local pf
  pf=$(pid_file "$name")
  if [[ -f "$pf" ]]; then
    local pid
    pid=$(cat "$pf")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid"
      echo "[$name] tunnel stopped (pid $pid)"
    else
      echo "[$name] was not running"
    fi
    rm -f "$pf"
  else
    echo "[$name] no pid file found"
  fi
}

tunnel_status() {
  for name in $(get_tunnel_names); do
    local lport rport desc
    lport=$(get_tunnel_field "$name" "localPort")
    rport=$(get_tunnel_field "$name" "remotePort")
    desc=$(get_tunnel_field "$name" "description")
    if is_running "$name"; then
      echo "  [UP]   $name  localhost:$lport -> $HOST:$rport  ($desc)  pid=$(cat "$(pid_file "$name")")"
    else
      echo "  [DOWN] $name  localhost:$lport -> $HOST:$rport  ($desc)"
    fi
  done
}

cmd="${1:-}"
shift || true

case "$cmd" in
  up)
    if [[ -n "${1:-}" ]]; then
      tunnel_up "$1"
    else
      for name in $(get_tunnel_names); do tunnel_up "$name"; done
    fi
    ;;
  down)
    if [[ -n "${1:-}" ]]; then
      tunnel_down "$1"
    else
      for name in $(get_tunnel_names); do tunnel_down "$name"; done
    fi
    ;;
  status)
    echo "Tunnels to $HOST:"
    tunnel_status
    ;;
  list)
    echo "Available tunnels:"
    for name in $(get_tunnel_names); do
      echo "  $name: localhost:$(get_tunnel_field "$name" "localPort") -> $HOST:$(get_tunnel_field "$name" "remotePort") ($(get_tunnel_field "$name" "description"))"
    done
    ;;
  ssh)
    exec ssh "$HOST"
    ;;
  exec)
    exec ssh "$HOST" "$@"
    ;;
  test)
    echo "Testing tunnels to $HOST:"
    for name in $(get_tunnel_names); do
      lport=$(get_tunnel_field "$name" "localPort")
      desc=$(get_tunnel_field "$name" "description")
      if ! is_running "$name"; then
        echo "  [SKIP] $name — tunnel not running"
        continue
      fi
      code=$(curl -sk -o /dev/null -w "%{http_code}" --connect-timeout 3 "https://127.0.0.1:$lport/" 2>/dev/null || echo "000")
      if [[ "$code" != "000" ]]; then
        echo "  [OK]   $name  https://localhost:$lport -> HTTP $code  ($desc)"
      else
        echo "  [FAIL] $name  https://localhost:$lport -> no response  ($desc)"
      fi
    done
    ;;
  *)
    usage
    ;;
esac
