#!/bin/bash
# =============================================================
# SymbioSync Biometric Context Hook (UserPromptSubmit)
#
# Reads current biometric state from a local SymbioSync instance
# and injects a compact context line into the agent's message.
#
# If SymbioSync is not running, exits silently -- no error noise.
#
# Injected format example:
#   [SymbioSync: HR 72 BPM | Sleep 87 Good (7h 12m) | Ring 96% | Ferri 88% | 2 devices]
#
# Install: copy to ~/.letta/hooks/ and ensure executable
# Config: set SYMBIOSYNC_URL to override default (http://127.0.0.1:8080)
# =============================================================

SYMBIOSYNC_URL="${SYMBIOSYNC_URL:-http://127.0.0.1:8080}"

# --- Debug logging (set SYMBIOSYNC_DEBUG=1 to enable) ---
SYMBIOSYNC_DEBUG="${SYMBIOSYNC_DEBUG:-0}"
LOG_FILE="/tmp/letta-hook-symbiosync.log"

log() {
    if [ "$SYMBIOSYNC_DEBUG" = "1" ]; then
        echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] [symbiosync] $*" >> "$LOG_FILE"
    fi
}

log "=== Hook fired ==="

# Only process UserPromptSubmit
input=$(cat)
event_type=$(echo "$input" | jq -r '.event_type // empty')
log "event_type=$event_type"

if [ "$event_type" != "UserPromptSubmit" ]; then
    log "Wrong event type, exiting"
    exit 0
fi

# Fetch SymbioSync status (short timeout -- this must be fast)
status_json=$(curl -s --max-time 2 "${SYMBIOSYNC_URL}/api/status" 2>/dev/null)

if [ -z "$status_json" ] || [ "$status_json" = "null" ]; then
    log "SymbioSync not reachable, exiting silently"
    exit 0
fi

# Parse device data
device_count=$(echo "$status_json" | jq '[.devices // {} | to_entries[] | select(.value.connected == true)] | length' 2>/dev/null)

if [ "$device_count" = "0" ] || [ -z "$device_count" ]; then
    log "No connected devices, exiting"
    exit 0
fi

# Build context parts
parts=""

# Heart rate (from colmi device)
hr=$(echo "$status_json" | jq -r '[.devices | to_entries[] | select(.value.connected and .value.device_type == "colmi") | .value.status.heart_rate // 0] | first // 0' 2>/dev/null)
hr_age=$(echo "$status_json" | jq -r '[.devices | to_entries[] | select(.value.connected and .value.device_type == "colmi") | .value.status.last_hr_seconds_ago // null] | first' 2>/dev/null)

if [ "$hr" != "0" ] && [ "$hr" != "null" ] && [ -n "$hr" ]; then
    hr_fresh=""
    if [ "$hr_age" != "null" ] && [ -n "$hr_age" ]; then
        hr_age_int=$(printf "%.0f" "$hr_age" 2>/dev/null)
        if [ "$hr_age_int" -gt 120 ] 2>/dev/null; then
            hr_fresh=" (${hr_age_int}s ago)"
        fi
    fi
    parts="HR ${hr} BPM${hr_fresh}"
fi

# SpO2
spo2=$(echo "$status_json" | jq -r '[.devices | to_entries[] | select(.value.connected and .value.device_type == "colmi") | .value.status.spo2 // 0] | first // 0' 2>/dev/null)
if [ "$spo2" != "0" ] && [ "$spo2" != "null" ] && [ -n "$spo2" ]; then
    if [ -n "$parts" ]; then parts="$parts | "; fi
    parts="${parts}SpO2 ${spo2}%"
fi

# Sleep data
sleep_score=$(echo "$status_json" | jq -r '[.devices | to_entries[] | select(.value.connected and .value.device_type == "colmi") | .value.status.sleep.score // null] | first' 2>/dev/null)
sleep_label=$(echo "$status_json" | jq -r '[.devices | to_entries[] | select(.value.connected and .value.device_type == "colmi") | .value.status.sleep.score_label // null] | first' 2>/dev/null)
sleep_total=$(echo "$status_json" | jq -r '[.devices | to_entries[] | select(.value.connected and .value.device_type == "colmi") | .value.status.sleep.total_min // 0] | first // 0' 2>/dev/null)

if [ "$sleep_score" != "null" ] && [ -n "$sleep_score" ] && [ "$sleep_total" != "0" ]; then
    sleep_hours=$((sleep_total / 60))
    sleep_mins=$((sleep_total % 60))
    if [ -n "$parts" ]; then parts="$parts | "; fi
    parts="${parts}Sleep ${sleep_score} ${sleep_label} (${sleep_hours}h ${sleep_mins}m)"
fi

# Battery levels per device
batteries=""
while IFS= read -r line; do
    name=$(echo "$line" | jq -r '.name' 2>/dev/null)
    batt=$(echo "$line" | jq -r '.battery' 2>/dev/null)
    dtype=$(echo "$line" | jq -r '.type' 2>/dev/null)
    if [ "$batt" != "null" ] && [ "$batt" != "-1" ] && [ -n "$batt" ]; then
        # Use short name
        short_name="$name"
        case "$dtype" in
            colmi) short_name="Ring" ;;
            lovense) short_name=$(echo "$name" | sed 's/LVS-//' | cut -c1-10) ;;
        esac
        if [ -n "$batteries" ]; then batteries="$batteries, "; fi
        batteries="${batteries}${short_name} ${batt}%"
    fi
done < <(echo "$status_json" | jq -c '[.devices | to_entries[] | select(.value.connected) | {name: .value.name, battery: .value.status.battery, type: .value.device_type}] | .[]' 2>/dev/null)

if [ -n "$batteries" ]; then
    if [ -n "$parts" ]; then parts="$parts | "; fi
    parts="${parts}${batteries}"
fi

# Device count
if [ -n "$parts" ]; then parts="$parts | "; fi
parts="${parts}${device_count} device(s)"

# Inject context line
if [ -n "$parts" ]; then
    log "Injecting: [SymbioSync: $parts]"
    cat <<CONTEXT >&2
[SymbioSync: ${parts}]
CONTEXT
fi

log "=== Hook complete ==="
exit 0
