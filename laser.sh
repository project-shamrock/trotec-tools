#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_BASE="https://localhost:5001"
API_VERSION="1.0-OpenApi"
DEVICE_SN="Q42-3066"

# Load .env file if present
if [[ -f "$SCRIPT_DIR/.env" ]]; then
  set -a
  source "$SCRIPT_DIR/.env"
  set +a
fi

# Auth credentials from env
RUBY_EMAIL="${RUBY_EMAIL:?Set RUBY_EMAIL in .env}"
RUBY_PASSWORD="${RUBY_PASSWORD:?Set RUBY_PASSWORD in .env}"

usage() {
  echo "Usage: laser.sh <command> [args]"
  echo ""
  echo "Commands:"
  echo "  auth               Get a fresh JWT token (prints token)"
  echo "  pat                Generate a PersonalAccessToken"
  echo "  status             Show device and process status"
  echo "  processes          Show Ruby service process states"
  echo "  devices            List connected devices"
  echo "  designs            List uploaded designs"
  echo "  workbenches        List workbenches"
  echo "  queue              Show queue state"
  echo "  upload <file>      Upload an SVG/design file"
  echo "  move-z <mm>        Move Z stage (absolute position in mm, negative)"
  echo "  camera             Get table camera stream URL"
  echo "  version            Show Ruby software version"
  echo "  errors <code>      Look up an error code"
  echo ""
  echo "Environment:"
  echo "  RUBY_EMAIL         Login email (default: r.j.walters@gmail.com)"
  echo "  RUBY_PASSWORD      Login password"
}

get_token() {
  curl -sk "$API_BASE/api/User/SignIn" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$RUBY_EMAIL\",\"password\":\"$RUBY_PASSWORD\"}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])"
}

api_get() {
  local path="$1"
  local token
  token=$(get_token)
  curl -sk "$API_BASE$path" \
    -H "Authorization: Bearer $token" \
    -H "Accept: application/json" \
    -H "x-target-device: $DEVICE_SN"
}

api_put() {
  local path="$1"
  local token
  token=$(get_token)
  curl -sk "$API_BASE$path" \
    -X PUT \
    -H "Authorization: Bearer $token" \
    -H "Accept: application/json" \
    -H "Content-Type: application/json" \
    -H "x-target-device: $DEVICE_SN"
}

api_post() {
  local path="$1"
  shift
  local token
  token=$(get_token)
  curl -sk "$API_BASE$path" \
    -X POST \
    -H "Authorization: Bearer $token" \
    -H "Accept: application/json" \
    "$@"
}

openapi_get() {
  local path="$1"
  local token
  token=$(get_token)
  curl -sk "$API_BASE/api/OpenApi$path" \
    -H "Authorization: Bearer $token" \
    -H "x-api-version: $API_VERSION" \
    -H "Accept: application/json" \
    -H "x-target-device: $DEVICE_SN"
}

cmd="${1:-}"
shift || true

case "$cmd" in
  auth)
    get_token
    ;;
  pat)
    token=$(get_token)
    curl -sk "$API_BASE/api/User/GeneratePersonalAccessToken" \
      -X POST \
      -H "Authorization: Bearer $token" \
      -H "Accept: application/json"
    echo
    ;;
  status)
    echo "=== Device Status ==="
    openapi_get "/GetDeviceStatus" | python3 -m json.tool 2>/dev/null || echo "(no status)"
    echo ""
    echo "=== Devices ==="
    api_get "/api/Proxy/ListDevices" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for d in data:
    dev = d['device']
    print(f'  Serial:  {dev[\"serialNo\"]}')
    print(f'  Kind:    {dev[\"kind\"]}')
    print(f'  Valid:   {bool(dev[\"isValid\"])}')
    print(f'  Direct:  {bool(d[\"isDirectConnection\"])}')
    print(f'  Z range: {dev[\"zLimits\"][\"min\"]:.1f} to {dev[\"zLimits\"][\"max\"]:.1f} mm')
    print(f'  Work area: {dev[\"plateSetup\"][\"size\"][\"width\"]:.1f} x {dev[\"plateSetup\"][\"size\"][\"height\"]:.1f} mm')
    caps = ', '.join(dev.get('capabilities', []))
    print(f'  Capabilities: {caps}')
if not data:
    print('  No devices found')
" 2>/dev/null
    echo ""
    echo "=== Processes ==="
    api_get "/api/Diagnostics/GetProcessesState" | python3 -c "
import sys, json
for p in json.load(sys.stdin):
    err = ''
    if 'processError' in p:
        err = f' -> {p[\"processError\"].get(\"message\", str(p[\"processError\"]))}'
    state = p['processState']
    icon = '●' if state == 'Running' else '○'
    print(f'  {icon} {state:8s} {p[\"processName\"]}{err}')
" 2>/dev/null
    ;;
  processes)
    api_get "/api/Diagnostics/GetProcessesState" | python3 -c "
import sys, json
for p in json.load(sys.stdin):
    err = ''
    if 'processError' in p:
        err = f' -> {p[\"processError\"].get(\"message\", str(p[\"processError\"]))}'
    state = p['processState']
    icon = '●' if state == 'Running' else '○'
    print(f'  {icon} {state:8s} {p[\"processName\"]}{err}')
" 2>/dev/null
    ;;
  devices)
    api_get "/api/Proxy/ListDevices" | python3 -m json.tool
    ;;
  designs)
    openapi_get "/GetDesigns" | python3 -m json.tool
    ;;
  workbenches)
    openapi_get "/GetWorkbenches" | python3 -m json.tool
    ;;
  queue)
    api_get "/api/Queue/GetQueue?deviceSn=$DEVICE_SN" | python3 -m json.tool
    ;;
  upload)
    file="${1:-}"
    if [[ -z "$file" ]]; then
      echo "Usage: laser.sh upload <file>"
      exit 1
    fi
    if [[ ! -f "$file" ]]; then
      echo "Error: file not found: $file"
      exit 1
    fi
    echo "Uploading: $file"
    token=$(get_token)
    result=$(curl -sk "$API_BASE/api/FileUpload/Upload" \
      -X POST \
      -H "Authorization: Bearer $token" \
      -H "Accept: application/json" \
      -F "uploadedFile=@$file" \
      --max-time 60 2>&1)
    echo "Response: $result"
    # Also try OpenAPI Upload as fallback
    if echo "$result" | grep -q "ERR_"; then
      echo "Trying OpenAPI Upload endpoint..."
      pat=$(curl -sk "$API_BASE/api/User/GeneratePersonalAccessToken" \
        -X POST \
        -H "Authorization: Bearer $token" \
        -H "Accept: application/json" | tr -d '"')
      result2=$(curl -sk "$API_BASE/api/OpenApi/Upload" \
        -X POST \
        -H "Authorization: PersonalAccessToken $pat" \
        -H "x-api-version: $API_VERSION" \
        -H "Accept: application/json" \
        -F "uploadedFile=@$file" \
        --max-time 60 2>&1)
      echo "Response: $result2"
    fi
    # Also SCP to Windows desktop as backup
    echo "Copying to Windows desktop as backup..."
    scp "$file" trotec:"C:/Users/Shamrock/Desktop/$(basename "$file")" 2>/dev/null && \
      echo "File also available at C:\\Users\\Shamrock\\Desktop\\$(basename "$file")" || \
      echo "SCP copy failed (non-critical)"
    ;;
  move-z)
    z="${1:-}"
    if [[ -z "$z" ]]; then
      echo "Usage: laser.sh move-z <mm>  (e.g., -3 for 3mm down)"
      exit 1
    fi
    echo "Moving Z to $z mm..."
    result=$(api_put "/api/Device/MoveZ?z=$z")
    echo "Response: $result"
    ;;
  camera)
    echo "Camera stream: $API_BASE/api/OpenApi/GetTableCameraStream"
    echo "(Requires auth token)"
    ;;
  version)
    api_get "/api/Info/GetVersionInfo" | python3 -m json.tool
    ;;
  errors)
    code="${1:-}"
    if [[ -z "$code" ]]; then
      echo "Usage: laser.sh errors <code>  (e.g., ERR_QUEUE_000)"
      exit 1
    fi
    # Known error codes
    declare -A ERRORS=(
      ["ERR_QUEUE_000"]="No device connected/selected"
      ["ERR_QUEUE_007"]="Device not ready (may need homing or initialization)"
      ["ERR_DEVCOM_006"]="Table move rejected (check lid closed, key on)"
      ["ERR_GENERAL_000"]="General error (often parameter or session issue)"
      ["ERR_GENERAL_100"]="Parameter error (missing or invalid parameter)"
      ["ERR_FILEUPLOAD_002"]="File upload error (wrong field name or format)"
      ["ERR_FILEUPLOAD_004"]="No import in progress"
      ["ERR_SETTINGS_001"]="Settings error (device not configured)"
      ["ERR_TRB_005"]="Cloud config download failed (calibration)"
      ["ERR_TRB_012"]="Cloud config bad request"
      ["ERR_MATERIAL_020"]="Material import error (non-critical)"
    )
    if [[ -n "${ERRORS[$code]:-}" ]]; then
      echo "$code: ${ERRORS[$code]}"
    else
      echo "$code: Unknown error code"
    fi
    ;;
  *)
    usage
    ;;
esac
