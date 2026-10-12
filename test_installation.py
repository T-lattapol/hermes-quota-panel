import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class InstallationTests(unittest.TestCase):
    def test_installation_copies_only_program_files_to_an_isolated_user_prefix(self):
        self.assertIsNotNone(importlib.util.find_spec('install'), 'A user-local installer is required')
        from install import install
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            target = base / 'installed app'
            install(ROOT, target, base / 'config', base / 'data', autostart=True, extension=True)
            self.assertTrue((target / 'codex_panel.py').is_file())
            self.assertTrue(os.access(target / 'launch.sh', os.X_OK))
            self.assertFalse((target / 'panel_state.json').exists())
            self.assertFalse((target / 'tests').exists())
            self.assertFalse((target / 'auth.json').exists())
            self.assertEqual(json.loads((target / '.install-manifest.json').read_text())['application'], 'hermes-quota-panel')
            desktop = (base / 'config' / 'autostart' / 'hermes-quota-claude.desktop').read_text()
            self.assertIn(' --claude', desktop)
            self.assertIn('Exec="', desktop)
            self.assertTrue((base / 'data' / 'gnome-shell' / 'extensions' / 'quota-direct-click@hermes-quota-panel' / 'metadata.json').exists())

    def test_installer_does_not_overwrite_an_unrelated_existing_directory(self):
        self.assertIsNotNone(importlib.util.find_spec('install'))
        from install import install
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            target = base / 'unrelated'
            target.mkdir()
            (target / 'keep.txt').write_text('User-owned content')
            with self.assertRaises(FileExistsError):
                install(ROOT, target, base / 'config', base / 'data')
            self.assertEqual((target / 'keep.txt').read_text(), 'User-owned content')


if __name__ == '__main__':
    unittest.main()
