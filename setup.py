"""Convenience one-command source-checkout setup coordinator.

Everything that touches the real machine (sudo/apt-get, Hermes discovery,
persisted config, the file installer, launching the viewer, enabling the
optional GNOME extension) is reached through keyword-injectable callables
with lazily-imported defaults. This lets tests exercise the full
coordination logic with zero real system side effects, and lets setup.py
run standalone once the sibling modules (setup_support.py, configuration.py)
exist without setup.py needing to know their import-time details.

Usage: ./setup.sh [--dry-run] [--no-packages] [--no-start] [--no-extension]
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
GUI_PACKAGES = ('python3-gi', 'gir1.2-gtk-3.0', 'gir1.2-ayatanaappindicator3-0.1', 'librsvg2-common')
OLD_AUTOSTART_NAMES = ('codex-quota.desktop', 'claude-quota.desktop')
EXTENSION_ID = 'quota-direct-click@hermes-quota-panel'


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true',
                         help='Print the plan; write, install, or start nothing')
    parser.add_argument('--no-packages', action='store_true',
                         help='Never run apt-get, even with interactive confirmation')
    parser.add_argument('--no-start', action='store_true',
                         help='Install and autostart, but do not launch the viewer now')
    parser.add_argument('--no-extension', action='store_true',
                         help='Skip the optional GNOME direct-click extension entirely')
    parser.add_argument('--prefix', type=Path, default=None,
                         help='Installation directory (default: $XDG_DATA_HOME/hermes-quota-panel)')
    return parser


def _status(message):
    print(message)


def default_detect_missing_packages(env=None, probe_python='/usr/bin/python3', runner=subprocess.run):
    """Probe real GI imports; return the subset of GUI_PACKAGES missing."""
    probes = {
        'python3-gi': "import gi",
        'gir1.2-gtk-3.0': "import gi; gi.require_version('Gtk','3.0'); from gi.repository import Gtk",
        'gir1.2-ayatanaappindicator3-0.1':
            "import gi; gi.require_version('AyatanaAppIndicator3','0.1'); "
            "from gi.repository import AyatanaAppIndicator3",
        'librsvg2-common': "import gi; gi.require_version('GdkPixbuf','2.0'); from gi.repository import GdkPixbuf; GdkPixbuf.Pixbuf.new_from_file(" + repr(str(APP_DIR / 'icons' / 'openai.svg')) + ')',
    }
    from launcher import gui_environment
    from configuration import read_settings
    base_env = dict(os.environ if env is None else env)
    probe_env = gui_environment({**base_env, **read_settings(base_env)})
    probe_python = probe_env.get('QUOTA_PANEL_GUI_PYTHON') or probe_python
    missing = []
    for package, code in probes.items():
        try:
            result = runner([probe_python, '-c', code], env=probe_env, capture_output=True, text=True, timeout=15)
            if result.returncode != 0:
                missing.append(package)
        except (OSError, subprocess.TimeoutExpired):
            missing.append(package)
    return missing


def _maybe_install_packages(missing, args, apt_install, input_fn, isatty):
    """Never installs silently. Returns True if apt-get actually ran."""
    if not missing or args.no_packages or args.dry_run:
        return False
    command = 'sudo apt-get install -y ' + ' '.join(missing)
    if not isatty():
        _status(f'Missing GUI packages: {", ".join(missing)}')
        _status(f'Non-interactive session: not running sudo automatically. Run manually:\n  {command}')
        return False
    answer = input_fn(f'Install missing packages now? [{", ".join(missing)}] (y/N): ')
    if str(answer).strip().lower() not in ('y', 'yes'):
        _status(f'Skipped package install. Run manually if needed:\n  {command}')
        return False
    apt_install(missing)
    return True


def default_find_conflicts(env=None, config_home=None, list_processes=None):
    """Detect a running viewer or a legacy (pre-rename) autostart entry."""
    def _list_processes():
        try:
            result = subprocess.run(['ps', '-eo', 'args'], capture_output=True, text=True, timeout=5)
            return result.stdout.splitlines()
        except (OSError, subprocess.TimeoutExpired):
            return []

    list_processes = list_processes or _list_processes
    running = any('codex_panel.py' in line for line in list_processes())
    autostart_dir = Path(config_home) / 'autostart' if config_home else None
    old_autostart = []
    if autostart_dir and autostart_dir.is_dir():
        old_autostart = [name for name in OLD_AUTOSTART_NAMES if (autostart_dir / name).exists()]
    return {'running': running, 'old_autostart': old_autostart}


def default_start_viewer(provider, env=None, destination=None):
    destination = Path(destination) if destination is not None else APP_DIR
    flags = ['--claude'] if provider == 'claude' else []
    subprocess.Popen([str(destination / 'launch.sh'), *flags], cwd=str(destination), env=env,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def main(argv=None, *, env=None, discover_hermes=None, write_config=None,
         install_fn=None, find_conflicts=None, start_viewer=None,
         detect_missing_packages=None, enable_extension=None,
         apt_install=None, input_fn=input, isatty=None):
    args = build_parser().parse_args(argv)
    env = dict(env if env is not None else os.environ)
    isatty = isatty if isatty is not None else sys.stdin.isatty

    if discover_hermes is None:
        from setup_support import discover_hermes
    try:
        hermes = discover_hermes(env=env)
    except RuntimeError as error:
        _status(f'Hermes setup check failed: {error}')
        _status('Set HERMES_AGENT_DIR/HERMES_PYTHON/HERMES_HOME, or install/clone Hermes first.')
        return 1

    data_home = Path(env.get('XDG_DATA_HOME', str(Path.home() / '.local' / 'share')))
    config_home = Path(env.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    destination = args.prefix or (data_home / 'hermes-quota-panel')

    detect_missing_packages = detect_missing_packages or default_detect_missing_packages
    missing = detect_missing_packages(env=env)

    plan = {
        'dry_run': bool(args.dry_run),
        'destination': str(destination),
        'hermes': hermes,
        'autostart': True,
        'extension': not args.no_extension,
        'start': not args.no_start,
        'missing_packages': missing,
    }

    if args.dry_run:
        _status('Setup plan (nothing written, installed, or started):')
        _status(json.dumps(plan, indent=2))
        return 0

    if missing:
        apt_install = apt_install or (lambda packages: subprocess.run(
            ['sudo', 'apt-get', 'install', '-y', *packages], check=True))
        try:
            installed = _maybe_install_packages(missing, args, apt_install, input_fn, isatty)
        except (OSError, subprocess.CalledProcessError):
            _status('Package installation failed. No viewer started; resolve the apt/sudo error and retry.')
            return 1
        if not installed:
            _status('Setup stopped: required desktop libraries are missing. No viewer started.')
            return 1

    if write_config is None:
        from setup_support import write_config
    write_config(dict(hermes), config_home=config_home)

    find_conflicts = find_conflicts or default_find_conflicts
    conflicts = find_conflicts(env=env, config_home=config_home)
    has_conflict = bool(conflicts.get('running') or conflicts.get('old_autostart'))
    if has_conflict:
        _status('Existing quota viewer or legacy autostart entry detected.')
        _status('Installing files only; leaving autostart and the running process untouched.')
        _status('Migrate manually: stop the old viewer and remove its autostart entries, then re-run setup.sh.')

    install_fn = install_fn or __import__('install').install
    install_fn(str(APP_DIR), str(destination), str(config_home), str(data_home),
               autostart=not has_conflict, extension=not args.no_extension)

    if not args.no_extension and enable_extension is not None:
        try:
            enable_extension()
        except Exception as error:  # best-effort, never fatal
            _status(f'Extension not enabled automatically ({error}); enable manually after next login if desired.')

    if not args.no_start and not has_conflict:
        start_viewer = start_viewer or (lambda provider, env=None: default_start_viewer(provider, env=env, destination=destination))
        for provider in ('codex', 'claude'):
            start_viewer(provider, env=env)
        _status('Started Codex and Claude viewers.')
    else:
        _status('Viewer not started automatically (see above).')

    _status('Setup complete.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
