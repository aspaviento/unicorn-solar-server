#!/usr/bin/env bash
# Generic Linux example. The bundled inputs are fictional, not live telemetry.
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${DATA_DIR:-$SCRIPT_DIR/mock-data}"
PANEL_API_URL="${PANEL_API_URL:-http://127.0.0.1:9001}"
export TZ="${PANEL_TIMEZONE:-Etc/UTC}"
apply=false
simulated_time=""

usage() {
	echo "Usage: $0 [--dry-run|--apply] [--at ISO_DATETIME]"
	echo "Environment: DATA_DIR, PANEL_API_URL, PANEL_TIMEZONE (IANA; default Etc/UTC)"
	echo "--at is permitted only in dry-run mode. Default: --dry-run."
}

while (($#)); do
	case "$1" in
	--dry-run) apply=false ;;
	--apply) apply=true ;;
	--at)
		[[ $# -ge 2 ]] || {
			usage >&2
			exit 2
		}
		simulated_time="$2"
		shift
		;;
	--help)
		usage
		exit 0
		;;
	*)
		usage >&2
		exit 2
		;;
	esac
	shift
done
if $apply && [[ -n "$simulated_time" ]]; then
	echo "--at cannot be combined with --apply" >&2
	exit 2
fi
for command in jq python3; do
	command -v "$command" >/dev/null || {
		echo "Required command: $command" >&2
		exit 1
	}
done
if $apply; then
	for command in curl flock; do
		command -v "$command" >/dev/null || {
			echo "Required command: $command" >&2
			exit 1
		}
	done
	# All invocations controlling this panel should share the same DATA_DIR.
	exec 9>"$DATA_DIR/.panel-cron.lock"
	flock -n 9 || {
		echo "Another panel update is running; skipped"
		exit 0
	}
fi

# Python's standard library handles IANA time zones and DST without GNU date.
# A failure here aborts before any HTTP request.
daylight_times="$(
	python3 - "$DATA_DIR/daylight.json" "$TZ" "$simulated_time" <<'PYTHON'
import json
import re
import sys
from datetime import datetime, time
from zoneinfo import ZoneInfo

try:
    zone = ZoneInfo(sys.argv[2])
    current = datetime.fromisoformat(sys.argv[3]) if sys.argv[3] else datetime.now(zone)
    if current.tzinfo is None:
        raise ValueError("--at must include a UTC offset")
    current = current.astimezone(zone)
    with open(sys.argv[1]) as stream:
        daylight = json.load(stream)
    if daylight['date'] != current.date().isoformat():
        raise ValueError("daylight data must be refreshed for today's local date")
    boundaries = []
    for key in ('sunrise', 'sunset'):
        value = daylight[key]
        if not isinstance(value, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value):
            raise ValueError("sunrise and sunset must use HH:MM")
        boundaries.append(datetime.combine(current.date(), time.fromisoformat(value), zone).timestamp())
    if boundaries[0] >= boundaries[1]:
        raise ValueError("expected sunrise before sunset")
    print(int(current.timestamp()), *(int(value) for value in boundaries))
except (OSError, ValueError, KeyError, TypeError) as error:
    sys.exit(f"Invalid daylight configuration: {error}; no panel updates sent")
PYTHON
)"
read -r now sunrise sunset <<<"$daylight_times"

post() {
	local endpoint="$1" payload="$2"
	if $apply; then
		curl --fail --silent --show-error --connect-timeout 5 --max-time 15 \
			-H 'Content-Type: application/json' --data-binary "$payload" \
			"${PANEL_API_URL%/}$endpoint" >/dev/null
		echo "Sent $endpoint"
	else
		printf 'DRY RUN: POST %s%s %s\n' "${PANEL_API_URL%/}" "$endpoint" "$payload"
	fi
}

if ((now < sunrise || now >= sunset)); then
	# Check this BEFORE reading/querying battery or tariff sources.
	# Never send tariff or battery updates here: either would wake the panel.
	post /api/standby '{}'
	exit 0
fi

battery="$(jq -ce '
    select((.percentage | type == "number") and .percentage >= 0 and .percentage <= 100)
    | select(.flow == "charging" or .flow == "discharging" or .flow == "exporting")
    | select(.flow != "exporting" or .percentage == 100)
    | {percentage, flow}
' "$DATA_DIR/battery.json")" || {
	echo "Missing or invalid battery data; no panel updates sent" >&2
	exit 1
}
tariff="$(jq -ce 'select(.level == "low" or .level == "medium" or .level == "high") | {level}' "$DATA_DIR/tariff.json")" || {
	echo "Missing or invalid tariff data; no panel updates sent" >&2
	exit 1
}
# Both input payloads are validated before either request is sent.
post /api/battery "$battery"
post /api/tariff "$tariff"
