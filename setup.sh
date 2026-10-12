#!/usr/bin/env bash
# Convenient one-command setup for a cloned Hermes Quota Panel checkout.
# Validates the environment, detects Hermes, persists settings, installs
# and autostarts the viewer for the current user, and starts it now when
# nothing else is already running. See `python3 setup.py --help` for flags
# (--dry-run, --no-packages, --no-start, --no-extension).
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-$0}")" >/dev/null 2>&1 && pwd -P)"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found on PATH. Install Python 3, then re-run ./setup.sh" >&2
    exit 1
fi

exec python3 "$SCRIPT_DIR/setup.py" "$@"
