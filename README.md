# Hermes Quota Panel

A Linux desktop quota viewer for **OpenAI Codex** and **Claude**, using accounts already configured in Hermes Agent. This is an unofficial, experimental desktop companion — not an OpenAI, Anthropic, or Nous Research product.

## Features

- Top-bar session and weekly used-percentage labels.
- Colored quota bars, account selector, reset times, and refresh feedback.
- Shared position/size across provider panels; one visible provider at a time.
- Resizable full/compact modes, remembered separately.
- `Refreshing…` → real success checkmark → `Refresh` after 1.5 seconds.
- Optional GNOME direct-click extension: click again to hide.
- Optional Codex banked reset, **only after explicit confirmation**, and only from Default account.

## Tested environment and limitations

- Ubuntu 24.04, GNOME Shell 46, **X11**, GTK 3.
- Hermes source checkout `3b0dc776b6` (v0.21.7-derived).
- The optional direct-click extension supports GNOME 46 only. Without it, the ordinary AppIndicator menu is available.
- Wayland placement/restoration and other desktop environments are **not verified**.
- Hermes internal usage APIs can change. Run `doctor.py`; do not assume all Hermes releases are compatible.
- You need your own existing Hermes OAuth sign-ins. This repository contains **no accounts, tokens, or live quota data**.
- Timestamps default to `Asia/Bangkok` / ICT; `QUOTA_PANEL_TIMEZONE` can select another IANA timezone.

## Quick start

### Convenient one-command setup (recommended)

After cloning this private repository yourself (no curl-pipe-bash bootstrap):

```sh
./setup.sh --dry-run      # preview: checks env, prints the plan, writes/installs/starts nothing
./setup.sh                # checks GUI deps (asks before any sudo apt-get), detects Hermes,
                           # saves settings, installs + autostarts for your user, starts both viewers
```

- Only verified on **Ubuntu 24.04, GNOME Shell 46, X11**; no Windows/other-desktop promises.
- Missing GUI packages (`python3-gi`, GTK/AppIndicator/Rsvg typelibs) trigger an **interactive**
  confirmation before any `sudo apt-get install`. In a non-interactive shell, or with
  `--no-packages`, it never touches sudo — it just prints the exact command to run yourself.
- If Hermes can't be discovered or looks incompatible, setup stops with a clear message and a
  path override hint; it never installs, updates, or logs into Hermes, and never asks for secrets.
- If a quota viewer is already running, or a legacy `codex-quota.desktop` /
  `claude-quota.desktop` autostart entry exists, setup **does not** start anything or add a
  duplicate autostart entry — it stages the install and prints a manual-migration note instead.
- The optional GNOME 46 direct-click extension is copied best-effort; the Shell may need your
  next login to pick it up, so no "works everywhere instantly" claim is made.

Useful flags: `--dry-run`, `--no-packages`, `--no-start`, `--no-extension`. See
`python3 setup.py --help` for details.

### Manual steps (equivalent, more control)

Install desktop prerequisites (Ubuntu):

```sh
sudo apt-get install python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 librsvg2-common
```

Clone this repository, open the directory, and check prerequisites:

```sh
python3 doctor.py
./launch.sh             # Codex
./launch.sh --claude    # Claude, in another terminal
```

Hermes is normally discovered at `~/.hermes/hermes-agent`, with its native Python at `venv/bin/python`. Custom installation:

```sh
export HERMES_AGENT_DIR="$HOME/path/to/hermes-agent"
export HERMES_PYTHON="$HERMES_AGENT_DIR/venv/bin/python"
export HERMES_HOME="$HOME/.hermes"
python3 doctor.py
```

The GTK UI uses system Python; quota helpers use Hermes's own Python so neither installation needs to borrow the other's dependencies.

## Install for the current user

Preview, then install:

```sh
python3 install.py --dry-run --autostart --extension
python3 install.py --autostart --extension
```

- Copies **allowlisted program files only** into `~/.local/share/hermes-quota-panel`.
- Adds two explicitly requested autostart entries in `~/.config/autostart`.
- Does not start anything, copy credentials, modify Hermes settings, or use sudo.
- Does not enable an extension or restart GNOME automatically.

For direct click, save other work and log out/in when convenient. Then:

```sh
gnome-extensions enable quota-direct-click@hermes-quota-panel
```

Do not enable two quota direct-click extensions simultaneously. If migrating from an earlier personal copy, disable its direct-click extension and autostart entries yourself before enabling this version. The installer does not alter unrelated installations.

Autostart inherits the **desktop session's** environment, not exports made in an arbitrary terminal. Non-standard Hermes paths therefore need to be set in your session environment. For normal/default Hermes paths, no additional configuration is required.

## Account selection and safety

The selector changes **displayed usage**, not the bot's configured provider/account. Explicit-account reads are read-only and discard replies from obsolete requests. Default uses Hermes's normal account-resolution and token-maintenance behavior.

Only usable stored OAuth accounts are listed. A single Claude account can legitimately produce a single option. Codex keeps **Default** separate from explicitly named accounts: Default means Hermes's ambient resolution, which is not assumed to be the first stored pool entry. If you add accounts in Hermes, restart the viewer to refresh the list.

**Reset is not Refresh.** Reset spends one banked Codex credit. The viewer asks for confirmation, never resets automatically, and disables Reset for non-default selections. Do not automate confirmation clicks.

## State and configuration

Personal quota snapshots, selected accounts, layout, and lock files stay outside the checkout:

```text
~/.local/state/hermes-quota-panel/
```

Override paths with `XDG_STATE_HOME`, `XDG_DATA_HOME`, `XDG_CONFIG_HOME`, or `QUOTA_PANEL_STATE_DIR`. Optional settings:

| Variable | Meaning |
| --- | --- |
| `HERMES_HOME` | Hermes profile/auth home; defaults to `~/.hermes` |
| `HERMES_AGENT_DIR` | Hermes source directory |
| `HERMES_PYTHON` | Interpreter capable of importing the installed Hermes APIs |
| `QUOTA_PANEL_GUI_PYTHON` | GTK-capable interpreter; defaults to `/usr/bin/python3` |
| `QUOTA_PANEL_TIMEZONE` | IANA display timezone, default `Asia/Bangkok` |
| `QUOTA_PANEL_GI_ROOT` | Optional external unpacked-library `usr` directory, for developer testing; libraries are not bundled |

Do not publish the state directory or Hermes's auth files. To remove installation, remove the two `hermes-quota-*.desktop` entries and the installed application directory; personal state is separate and can be retained.

## Development and tests

Normal tests use explicitly **synthetic fixtures** and require no account credentials. GTK tests need a window manager, not just a virtual display:

```sh
sudo apt-get install xvfb openbox dbus-x11 x11-utils nodejs
dbus-run-session -- xvfb-run -a -s '-screen 0 2560x1440x24' sh tools/headless_test.sh
python3 tools/check_publish.py
```

Live helper tests are opt-in and make real quota API requests. They never consume reset credits:

```sh
RUN_LIVE_TESTS=1 python3 -m unittest test_account_helpers_live -v
```

See `SECURITY.md` before sharing. UI geometry tests should use a real GTK main loop so frame-clock driven resizing can complete. A missed frame under a loaded window manager can make a geometry assertion flaky; do not remove the assertions to hide failures.

## License

MIT for this project's source and original monogram SVG icons. Imported Python/GNOME libraries retain their own licenses. Provider names identify integrations; the included icons are **not official company logos**. See `LICENSE`.
