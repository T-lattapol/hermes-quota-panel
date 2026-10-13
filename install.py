"""User-local, allowlisted installation. No sudo, auth changes, or program startup."""
import argparse
import json
import os
import shutil
from pathlib import Path

APP_ID = 'hermes-quota-panel'
EXTENSION_ID = 'quota-direct-click@hermes-quota-panel'
PROGRAM_FILES = ('codex_panel.py', 'usage_details.py', 'quota_ui.py', 'panel_geometry.py',
                 'account_selector.py', 'claude_usage.py', 'anthropic_percent.py', 'codex_usage.py', 'codex_reset.py',
                 'runtime_paths.py', 'desktop_presence.py', 'configuration.py', 'setup_support.py', 'launcher.py', 'launch.sh', 'doctor.py')
EXTENSION_FILES = ('metadata.json', 'extension.js', 'click-routing.js', 'package.json')
MANAGED = '# Managed by hermes-quota-panel'


def desktop_quote(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$').replace('`', '\\`').replace('%', '%%') + '"'


def install(source, destination, config_home, data_home, *, autostart=False, extension=False):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    config_home, data_home = Path(config_home), Path(data_home)
    if source == destination:
        raise ValueError('Installation directory must differ from the source checkout')
    manifest = destination / '.install-manifest.json'
    if destination.exists() and any(destination.iterdir()):
        try:
            owned = json.loads(manifest.read_text()).get('application') == APP_ID
        except (OSError, ValueError, AttributeError):
            owned = False
        if not owned:
            raise FileExistsError('Refusing to overwrite a non-managed installation directory')
    for name in PROGRAM_FILES:
        if not (source / name).is_file():
            raise FileNotFoundError(f'Missing program file: {name}')
    desktop_paths = [config_home / 'autostart' / f'hermes-quota-{provider}.desktop' for provider in ('codex', 'claude')]
    if autostart:
        for path in desktop_paths:
            if path.exists() and MANAGED not in path.read_text():
                raise FileExistsError('Refusing to overwrite an unrelated autostart entry')
    destination.mkdir(parents=True, exist_ok=True)
    for name in PROGRAM_FILES:
        shutil.copy2(source / name, destination / name)
    (destination / 'icons').mkdir(exist_ok=True)
    for name in ('openai.svg', 'claude.svg'):
        shutil.copy2(source / 'icons' / name, destination / 'icons' / name)
    (destination / 'launch.sh').chmod(0o755)
    manifest.write_text(json.dumps({'application': APP_ID, 'files': list(PROGRAM_FILES)}, indent=2) + '\n')
    if autostart:
        for provider, path in zip(('codex', 'claude'), desktop_paths):
            path.parent.mkdir(parents=True, exist_ok=True)
            flags = ' --claude' if provider == 'claude' else ''
            path.write_text(MANAGED + '\n[Desktop Entry]\nType=Application\nName=Hermes quota — ' + provider.title() + '\nExec=' + desktop_quote(destination / 'launch.sh') + flags + '\nTerminal=false\nX-GNOME-Autostart-enabled=true\n')
    if extension:
        target = data_home / 'gnome-shell' / 'extensions' / EXTENSION_ID
        target.mkdir(parents=True, exist_ok=True)
        for name in EXTENSION_FILES:
            shutil.copy2(source / 'gnome-extension' / name, target / name)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    data_home = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local' / 'share')))
    config_home = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    parser.add_argument('--prefix', type=Path, default=data_home / APP_ID)
    parser.add_argument('--autostart', action='store_true', help='Create both user autostart entries')
    parser.add_argument('--extension', action='store_true', help='Copy optional GNOME 46 direct-click extension; do not enable it')
    parser.add_argument('--dry-run', action='store_true', help='Print intended actions without writing anything')
    args = parser.parse_args()
    if args.dry_run:
        print(json.dumps({'destination': str(args.prefix), 'program_files': list(PROGRAM_FILES),
                          'autostart': args.autostart, 'extension': args.extension}, indent=2))
        return
    target = install(Path(__file__).resolve().parent, args.prefix, config_home, data_home,
                     autostart=args.autostart, extension=args.extension)
    print(f'Installed: {target}')
    print('No processes started. No credentials copied or modified.')
    if args.extension:
        print(f'Log out/in when convenient, then optionally enable: gnome-extensions enable {EXTENSION_ID}')


if __name__ == '__main__':
    main()
