"""Load only non-secret viewer settings; never read Hermes auth stores."""
import json
import os
from pathlib import Path

ALLOWED_SETTINGS = frozenset({'HERMES_HOME', 'HERMES_AGENT_DIR', 'HERMES_PYTHON',
    'QUOTA_PANEL_TIMEZONE', 'QUOTA_PANEL_GUI_PYTHON', 'QUOTA_PANEL_GI_ROOT', 'QUOTA_PANEL_VISIBILITY'})


def config_path(env=None):
    env = os.environ if env is None else env
    home = Path(env.get('HOME') or str(Path.home()))
    base = Path(env.get('XDG_CONFIG_HOME') or str(home / '.config')).expanduser()
    return base / 'hermes-quota-panel' / 'config.json'


def safe_value(value):
    return isinstance(value, str) and bool(value) and not any(char in value for char in '\n\r\0')


def read_settings(env=None):
    env = os.environ if env is None else env
    try:
        document = json.loads(config_path(env).read_text())
    except (OSError, ValueError):
        document = {}
    if not isinstance(document, dict):
        document = {}
    settings = {key: value for key, value in document.items() if key in ALLOWED_SETTINGS and safe_value(value)}
    for key in ALLOWED_SETTINGS:
        if key in env and isinstance(env[key], str):
            if safe_value(env[key]):
                settings[key] = env[key]
            else:
                settings.pop(key, None)  # An explicit empty setting clears the saved override.
    return settings
