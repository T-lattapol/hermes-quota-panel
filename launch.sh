#!/bin/sh
set -eu
BASE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ "${1:-}" = "--help" ]; then
    printf '%s\n' 'Usage: launch.sh [--claude] [--details]' 'Default provider: Codex. Run python3 doctor.py to check prerequisites.'
    exit 0
fi
exec "${QUOTA_PANEL_GUI_PYTHON:-/usr/bin/python3}" "$BASE/launcher.py" "$@"
