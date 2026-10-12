"""Start GTK in its system Python with optional external GI libraries."""
import os
import sys
from pathlib import Path
from runtime_paths import APP_DIR


def gui_environment(env=None):
    env = dict(os.environ if env is None else env)
    root = env.get('QUOTA_PANEL_GI_ROOT')
    if root:
        # Optional externally installed libraries, never bundled in the repository.
        libraries = sorted((Path(root) / 'lib').glob('*-linux-gnu'))
        libraries = [folder for folder in libraries if folder.is_dir()]
        typelib = [str(folder / 'girepository-1.0') for folder in libraries]
        env['GI_TYPELIB_PATH'] = os.pathsep.join(typelib + ([env['GI_TYPELIB_PATH']] if env.get('GI_TYPELIB_PATH') else []))
        env['LD_LIBRARY_PATH'] = os.pathsep.join([str(folder) for folder in libraries] + ([env['LD_LIBRARY_PATH']] if env.get('LD_LIBRARY_PATH') else []))
    return env


if __name__ == '__main__':
    python = os.environ.get('QUOTA_PANEL_GUI_PYTHON', '/usr/bin/python3')
    os.execvpe(python, [python, str(APP_DIR / 'codex_panel.py'), *sys.argv[1:]], gui_environment())
