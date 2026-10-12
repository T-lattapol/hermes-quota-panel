import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class PublishGuardTests(unittest.TestCase):
    def test_auth_files_and_token_literals_are_rejected_without_echoing_secrets(self):
        self.assertTrue((ROOT / 'tools' / 'check_publish.py').is_file(), 'Publish audit is missing')
        from tools.check_publish import audit_files
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'auth.json').write_text('{}')
            sample = 'gh' + 'p_' + 'Z' * 40
            (root / 'accidental.py').write_text('value = ' + repr(sample))
            issues = audit_files(root, ['auth.json', 'accidental.py'])
            self.assertEqual(len(issues), 2)
            self.assertTrue(any('auth.json' in issue for issue in issues))
            self.assertFalse(any(sample in issue for issue in issues), 'Audit must never print offending credential text')

    def test_synthetic_fixtures_are_allowed_but_real_snapshot_names_are_not(self):
        self.assertTrue((ROOT / 'tools' / 'check_publish.py').is_file())
        from tools.check_publish import audit_files
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'tests' / 'fixtures').mkdir(parents=True)
            (root / 'tests' / 'fixtures' / 'example.json').write_text('{"fixture": true}')
            (root / 'panel_state.json').write_text('{}')
            issues = audit_files(root, ['tests/fixtures/example.json', 'panel_state.json'])
            self.assertEqual(len(issues), 1)
            self.assertIn('panel_state.json', issues[0])


if __name__ == '__main__':
    unittest.main()
