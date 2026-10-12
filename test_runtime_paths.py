"""Packaging checks; no credential files or network requests are needed."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class RuntimePathsTests(unittest.TestCase):
    def test_paths_are_configurable_and_independent_of_the_authors_machine(self):
        self.assertIsNotNone(importlib.util.find_spec('runtime_paths'), 'Portable runtime paths have not been added')
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            env = {**os.environ, 'HOME': str(home), 'XDG_STATE_HOME': str(home / 'state'),
                   'HERMES_HOME': str(home / 'auth'), 'HERMES_AGENT_DIR': str(home / 'agent'),
                   'HERMES_PYTHON': str(home / 'agent-python')}
            env.pop('QUOTA_PANEL_STATE_DIR', None)
            result = subprocess.run([sys.executable, '-c',
                'import json,runtime_paths as p; print(json.dumps([str(p.APP_DIR),str(p.STATE_DIR),str(p.HERMES_HOME),str(p.HERMES_ROOT),p.HERMES_PYTHON]))'],
                cwd=ROOT, env=env, text=True, capture_output=True, check=True)
            self.assertEqual(json.loads(result.stdout), [str(ROOT), str(home / 'state' / 'hermes-quota-panel'),
                str(home / 'auth'), str(home / 'agent'), str(home / 'agent-python')])

    def test_core_source_does_not_contain_absolute_home_directories(self):
        for name in ('codex_panel.py', 'usage_details.py', 'claude_usage.py', 'codex_usage.py', 'codex_reset.py'):
            with self.subTest(file=name):
                self.assertFalse('/home/' in (ROOT / name).read_text(), 'A machine-specific path would break installation')

    def test_persisted_paths_are_available_to_a_fresh_autostart_environment(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            config = home / 'config' / 'hermes-quota-panel'
            config.mkdir(parents=True)
            (config / 'config.json').write_text(json.dumps({
                'HERMES_PYTHON': str(home / 'native-python'), 'HERMES_AGENT_DIR': str(home / 'native-agent'),
                'HERMES_HOME': str(home / 'auth-home')}))
            env = {key: value for key, value in os.environ.items() if not key.startswith('HERMES_') and not key.startswith('QUOTA_PANEL_')}
            env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / 'config'))
            result = subprocess.run([sys.executable, '-c',
                'import json,runtime_paths as p; print(json.dumps([str(p.HERMES_HOME),str(p.HERMES_ROOT),p.HERMES_PYTHON]))'],
                cwd=ROOT, env=env, text=True, capture_output=True, check=True)
            self.assertEqual(json.loads(result.stdout), [str(home / 'auth-home'), str(home / 'native-agent'), str(home / 'native-python')])

    def test_empty_environment_settings_clear_saved_overrides_without_breaking_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            env = {key: value for key, value in os.environ.items() if not key.startswith('HERMES_') and not key.startswith('QUOTA_PANEL_')}
            env.update(HOME=folder, XDG_CONFIG_HOME=folder, HERMES_HOME='', HERMES_AGENT_DIR='', QUOTA_PANEL_TIMEZONE='')
            result = subprocess.run([sys.executable, '-c',
                'import json,runtime_paths as p; print(json.dumps([str(p.HERMES_HOME),str(p.HERMES_ROOT),p.TIMEZONE_LABEL]))'],
                cwd=ROOT, env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, 'Empty optional settings must not crash autostart')
            self.assertEqual(json.loads(result.stdout), [str(Path(folder) / '.hermes'), str(Path(folder) / '.hermes' / 'hermes-agent'), 'ICT'])


if __name__ == '__main__':
    unittest.main()
