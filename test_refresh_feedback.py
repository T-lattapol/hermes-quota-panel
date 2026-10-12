import json
from pathlib import Path
import unittest
from usage_details import UsageDetails
from test_button_effects import descendants
from gi.repository import Gtk


class RefreshFeedbackTests(unittest.TestCase):
    def test_click_acknowledges_pending_then_marks_real_completion(self):
        calls = []
        detail = UsageDetails('Codex', 'openai-codex', lambda: calls.append('fetch'), lambda _: None)
        data = json.loads((Path(__file__).resolve().parent / 'tests' / 'fixtures' / 'codex_snapshot.json').read_text())
        button = next(w for w in descendants(detail.window) if isinstance(w, Gtk.Button) and w.get_label() == 'Refresh')
        try:
            detail.update(data)
            button.emit('clicked')
            self.assertEqual(button.get_label(), 'Refreshing…')
            self.assertFalse(button.get_sensitive())
            button.emit('clicked')
            self.assertEqual(calls, ['fetch'], 'A pending refresh must not submit duplicate requests')
            detail.update(data)
            self.assertTrue(button.get_sensitive())
            self.assertEqual(button.get_label(), 'Refresh ✓')
        finally:
            detail.window.destroy()

    def test_failure_reenables_retry_without_success_message(self):
        calls = []
        detail = UsageDetails('Codex', 'openai-codex', lambda: calls.append('fetch'), lambda _: None)
        try:
            button = detail.refresh_button
            button.emit('clicked')
            detail.unavailable()
            self.assertTrue(button.get_sensitive())
            self.assertEqual(button.get_label(), 'Retry refresh')
            self.assertIn('failed', detail.status.get_text())
        finally:
            detail.window.destroy()

    def test_reopening_cached_data_does_not_claim_pending_refresh_finished(self):
        detail = UsageDetails('Codex', 'openai-codex', lambda: None, lambda _: None)
        try:
            detail.update(json.loads((Path(__file__).resolve().parent / 'tests' / 'fixtures' / 'codex_snapshot.json').read_text()))
            detail.refresh_button.emit('clicked')
            detail.hide()
            detail.show()
            self.assertEqual(detail.refresh_button.get_label(), 'Refreshing…')
            self.assertFalse(detail.refresh_button.get_sensitive())
            self.assertEqual(detail.status.get_text(), 'Refreshing…')
        finally:
            detail.window.destroy()


if __name__ == '__main__':
    unittest.main()
