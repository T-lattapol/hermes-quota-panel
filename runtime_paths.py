"""Machine-independent paths; importing this module never reads credentials."""
import os
import shutil
from pathlib import Path
from zoneinfo import ZoneInfo

APP_DIR = Path(__file__).resolve().parent
HERMES_HOME = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes'))).expanduser().resolve()
HERMES_ROOT = Path(os.environ.get('HERMES_AGENT_DIR', str(HERMES_HOME / 'hermes-agent'))).expanduser().resolve()
_default_python = HERMES_ROOT / 'venv' / 'bin' / 'python'
HERMES_PYTHON = os.environ.get('HERMES_PYTHON') or (str(_default_python) if _default_python.is_file() else shutil.which('python3') or '/usr/bin/python3')
STATE_DIR = Path(os.environ.get('QUOTA_PANEL_STATE_DIR') or str(Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local' / 'state'))) / 'hermes-quota-panel')).expanduser().resolve()
HELPER_ENV = {**os.environ, 'HERMES_HOME': str(HERMES_HOME),
              'PYTHONPATH': os.pathsep.join(filter(None, [str(HERMES_ROOT), str(APP_DIR), os.environ.get('PYTHONPATH', '')]))}
DISPLAY_ZONE = ZoneInfo(os.environ.get('QUOTA_PANEL_TIMEZONE', 'Asia/Bangkok'))
TIMEZONE_LABEL = 'ICT' if DISPLAY_ZONE.key == 'Asia/Bangkok' else DISPLAY_ZONE.key
