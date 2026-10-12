#!/bin/sh
# Run inside xvfb-run and a fresh dbus-run-session, not in the user's desktop.
set -eu
openbox >"${TMPDIR:-/tmp}/hermes-quota-openbox.log" 2>&1 &
WM_PID=$!
trap 'kill "$WM_PID" 2>/dev/null || true' EXIT HUP INT TERM
python3 tools/wait_for_wm.py
/usr/bin/python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/test_direct_click.mjs
node --check gnome-extension/extension.js
