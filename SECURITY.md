# Privacy and safety

- No credential files, live quota snapshots, personal account choices, layouts, logs, or downloaded libraries belong in Git.
- OAuth tokens are resolved at runtime from your own installed Hermes. Account-list output contains only safe local IDs/labels/priority/default metadata.
- Personal state lives in the user's XDG state directory, outside the source tree. It can still contain private account labels; do not share it.
- Explicit-account reads do not rotate credentials on failure. Default uses the installed Hermes's normal auth-resolution behavior.
- Switching account drops old quota immediately; request generations prevent an old account's reply from overwriting a new one.
- Codex Reset is opt-in, confirmation-gated, and blocked for non-default selections. Automated tests never consume a reset credit.
- CI has no Hermes credentials. Live tests are skipped unless `RUN_LIVE_TESTS=1` is explicitly set locally.
- Run `python3 tools/check_publish.py` against staged/tracked source before pushing. It reports only file names/reasons, never credential values.
- If a token ever enters Git, removing the file is not sufficient. Stop publishing that history and revoke the credential through its provider.
- Do not include auth data, headers, or complete API responses when reporting a bug. Submit redacted errors and environment/version information instead.
