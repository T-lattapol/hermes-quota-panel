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


if __name__ == '__main__':
    unittest.main()
