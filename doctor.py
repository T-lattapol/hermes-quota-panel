"""Read-only prerequisite check. Does not load accounts, refresh tokens, or call quota APIs."""
import argparse
import json
import os
import subprocess
from launcher import gui_environment
from runtime_paths import HERMES_PYTHON, HELPER_ENV, HERMES_ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    checks = {}
    gui_python = os.environ.get('QUOTA_PANEL_GUI_PYTHON', '/usr/bin/python3')
    probes = {
        'GTK3 and Ayatana': ([gui_python, '-c', "import gi; gi.require_version('Gtk','3.0'); gi.require_version('AyatanaAppIndicator3','0.1'); from gi.repository import Gtk,AyatanaAppIndicator3"], gui_environment()),
        'Hermes usage API': ([HERMES_PYTHON, '-c', "from agent.account_usage import fetch_account_usage,redeem_codex_reset_credit,_fetch_anthropic_account_usage,_resolve_codex_usage_credentials; from agent.credential_pool import read_credential_pool,PooledCredential; from hermes_cli.subcommands.usage import usage_snapshot_document"], HELPER_ENV),
    }
    for name, (command, env) in probes.items():
        try:
            result = subprocess.run(command, env=env, text=True, capture_output=True, timeout=15)
            checks[name] = result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            checks[name] = False
    checks['Desktop display'] = bool(os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'))
    if args.json:
        print(json.dumps({'checks': checks, 'hermes_source': str(HERMES_ROOT)}, indent=2))
    else:
        for name, ok in checks.items():
            print(('OK   ' if ok else 'FAIL ') + name)
        if not checks['GTK3 and Ayatana']:
            print('Install system python3-gi, gir1.2-gtk-3.0, gir1.2-ayatanaappindicator3-0.1.')
        if not checks['Hermes usage API']:
            print('Check HERMES_AGENT_DIR and HERMES_PYTHON; see README for supported setup.')
        if os.environ.get('XDG_SESSION_TYPE') == 'wayland':
            print('WARNING: Window positioning is only verified on X11.')
    raise SystemExit(0 if all(checks.values()) else 1)


if __name__ == '__main__':
    main()
