import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


class ConfigurationTests(unittest.TestCase):
    def test_saved_paths_are_loaded_without_importing_credential_fields(self):
        self.assertIsNotNone(importlib.util.find_spec('configuration'), 'Persistent setup settings have not been added')
        from configuration import read_settings
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            directory = home / 'config' / 'hermes-quota-panel'
            directory.mkdir(parents=True)
            (directory / 'config.json').write_text(json.dumps({
                'HERMES_PYTHON': '/custom env/bin/python',
                'HERMES_AGENT_DIR': '/custom agent',
                'access_token': 'synthetic value that must not be returned'}))
            settings = read_settings({'HOME': str(home), 'XDG_CONFIG_HOME': str(home / 'config')})
            self.assertEqual(settings, {'HERMES_PYTHON': '/custom env/bin/python', 'HERMES_AGENT_DIR': '/custom agent'})

    def test_explicit_environment_overrides_saved_values(self):
        from configuration import read_settings
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder) / 'hermes-quota-panel'
            directory.mkdir()
            (directory / 'config.json').write_text(json.dumps({'HERMES_PYTHON': '/saved/python'}))
            settings = read_settings({'XDG_CONFIG_HOME': folder, 'HERMES_PYTHON': '/explicit/python', 'API_KEY': 'not a configuration setting'})
            self.assertEqual(settings, {'HERMES_PYTHON': '/explicit/python'})


if __name__ == '__main__':
    unittest.main()
