import importlib.util
import json
import stat
import tempfile
import unittest
from pathlib import Path


class SetupSupportTests(unittest.TestCase):
    def test_setup_saves_private_non_secret_settings_for_later_autostart(self):
        self.assertIsNotNone(importlib.util.find_spec('setup_support'), 'Hermes setup helpers are missing')
        from setup_support import write_config
        with tempfile.TemporaryDirectory() as folder:
            path = write_config({'HERMES_AGENT_DIR': '/custom agent', 'HERMES_PYTHON': '/custom agent/venv/bin/python'}, config_home=Path(folder))
            self.assertEqual(path, Path(folder) / 'hermes-quota-panel' / 'config.json')
            self.assertEqual(json.loads(path.read_text())['HERMES_AGENT_DIR'], '/custom agent')
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_credentials_are_rejected_before_any_file_is_written(self):
        from setup_support import write_config
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                write_config({'access_token': 'synthetic test value'}, config_home=Path(folder))
            self.assertFalse((Path(folder) / 'hermes-quota-panel').exists())

    def test_discovery_validates_standard_hermes_without_reading_credentials(self):
        import json
        from unittest.mock import patch, Mock
        import setup_support
        self.assertTrue(hasattr(setup_support, 'discover_hermes'), 'Automatic Hermes discovery is missing')
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            root = home / '.hermes' / 'hermes-agent'
            python = root / 'venv' / 'bin' / 'python'
            python.parent.mkdir(parents=True)
            python.touch()
            completed = Mock(returncode=0, stdout=json.dumps({'root': str(root), 'python': str(python)}))
            with patch('setup_support.subprocess.run', return_value=completed) as run:
                settings = setup_support.discover_hermes({'HOME': str(home), 'PATH': '/nonexistent'})
            self.assertEqual(settings, {'HERMES_HOME': str(home / '.hermes'), 'HERMES_AGENT_DIR': str(root), 'HERMES_PYTHON': str(python)})
            probe = run.call_args.args[0]
            self.assertEqual(probe[0], str(python))
            self.assertNotIn('read_credential_pool(', probe[-1])
            self.assertNotIn('fetch_account_usage(', probe[-1])

    def test_nonstandard_hermes_is_found_from_the_cli_shebang(self):
        from unittest.mock import patch, Mock
        import setup_support
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            root = home / 'custom agent'
            python = root / 'venv' / 'bin' / 'python'
            python.parent.mkdir(parents=True)
            python.touch()
            bin_dir = home / 'bin'
            bin_dir.mkdir()
            cli = bin_dir / 'hermes'
            cli.write_text('#!' + str(python) + '\n# Synthetic CLI wrapper for discovery test\n')
            cli.chmod(0o755)
            def probe(command, **kwargs):
                if command[0] != str(python):
                    raise FileNotFoundError('not the test interpreter')
                return Mock(returncode=0, stdout=json.dumps({'root': str(root), 'python': str(python)}))
            with patch('setup_support.subprocess.run', side_effect=probe):
                try:
                    settings = setup_support.discover_hermes({'HOME': str(home), 'PATH': str(bin_dir)})
                except RuntimeError:
                    self.fail('The installed hermes CLI should reveal its interpreter automatically')
            self.assertEqual(settings['HERMES_PYTHON'], str(python))
            self.assertEqual(settings['HERMES_AGENT_DIR'], str(root))

    def test_invalid_explicit_python_is_not_silently_replaced(self):
        from unittest.mock import patch, Mock
        import setup_support
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            cli = home / 'hermes'
            cli.write_text('#!/valid/python\n')
            cli.chmod(0o755)
            def probe(command, **kwargs):
                if command[0] == '/invalid/explicit-python':
                    raise FileNotFoundError('configured interpreter is absent')
                return Mock(returncode=0, stdout=json.dumps({'root': '/valid/agent', 'python': '/valid/python'}))
            with patch('setup_support.shutil.which', return_value=str(cli)), patch('setup_support.subprocess.run', side_effect=probe):
                with self.assertRaises(RuntimeError):
                    setup_support.discover_hermes({'HOME': str(home), 'PATH': folder, 'HERMES_PYTHON': '/invalid/explicit-python'})


if __name__ == '__main__':
    unittest.main()
