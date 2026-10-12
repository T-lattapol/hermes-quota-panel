import json
from pathlib import Path
import unittest
from usage_details import UsageDetails


class SelectedAccountResetTests(unittest.TestCase):
    def test_non_default_codex_account_cannot_open_reset_dialog(self):
        calls = []
        detail = UsageDetails('Codex', 'openai-codex', lambda: None, calls.append)
        try:
            data = json.loads((Path(__file__).resolve().parents[1] / 'tests' / 'fixtures' / 'codex_snapshot.json').read_text())
            data['reset_allowed'] = False
            detail.update(data)
            self.assertFalse(detail.reset_button.get_sensitive())
            self.assertIn('default account', detail.reset_note.get_text())
            detail.confirm_reset()
            self.assertEqual(calls, [])
        finally:
            detail.window.destroy()


if __name__ == '__main__':
    unittest.main()
