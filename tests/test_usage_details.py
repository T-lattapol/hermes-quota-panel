import json
from pathlib import Path
import unittest
from unittest.mock import patch
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from usage_details import UsageDetails
from quota_ui import usage_color, reset_credits

class UsageDetailsTests(unittest.TestCase):
    def test_minimize_hides_panel_and_show_restores_it(self):
        import time
        for name, provider in [('Codex', 'openai-codex'), ('Claude', 'anthropic')]:
            with self.subTest(provider=provider):
                detail = UsageDetails(name, provider, lambda: None, lambda _: self.fail('Must not reset'))
                try:
                    detail.show()
                    deadline = time.monotonic() + 0.3
                    while time.monotonic() < deadline:
                        while Gtk.events_pending():
                            Gtk.main_iteration_do(False)
                        time.sleep(0.01)
                    header = detail.window.get_titlebar()
                    self.assertIsNotNone(header, 'Panel needs a working hide button in its titlebar')
                    hide_button = next((child for child in header.get_children()
                                        if isinstance(child, Gtk.Button) and child.get_tooltip_text() == 'Hide panel'), None)
                    self.assertIsNotNone(hide_button, 'Titlebar must offer Hide panel')
                    hide_button.emit('clicked')
                    deadline = time.monotonic() + 2
                    while detail.window.get_visible() and time.monotonic() < deadline:
                        while Gtk.events_pending():
                            Gtk.main_iteration_do(False)
                        time.sleep(0.01)
                    self.assertFalse(detail.window.get_visible(), 'Minimize must hide the panel, not leave it visible')
                    detail.show()
                    deadline = time.monotonic() + 0.3
                    while time.monotonic() < deadline:
                        while Gtk.events_pending():
                            Gtk.main_iteration_do(False)
                        time.sleep(0.01)
                    self.assertTrue(detail.window.get_visible())
                    self.assertTrue(detail.window.get_mapped(), 'Panel must reopen after minimizing')
                finally:
                    detail.window.destroy()

    def test_live_snapshot_renders_colored_bars_and_cancel_does_not_reset(self):
        data = json.loads((Path(__file__).resolve().parents[1] / 'tests' / 'fixtures' / 'codex_snapshot.json').read_text())
        calls = []
        detail = UsageDetails('Codex', 'openai-codex', lambda: None, calls.append)
        detail.update(data)
        windows = {w['label']: w for w in data['windows']}
        for key, (_, bar, _) in detail.rows.items():
            self.assertAlmostEqual(bar.get_fraction(), windows[key]['used_percent'] / 100)
            self.assertTrue(bar.get_style_context().has_class(usage_color(windows[key]['used_percent'])))
        self.assertEqual(detail.reset_button.get_sensitive(), reset_credits(data) > 0)
        test = self
        def cancel(dialog):
            exhausted = any(w['used_percent'] >= 100 for w in windows.values())
            test.assertEqual(dialog.get_widget_for_response(Gtk.ResponseType.OK).get_sensitive(), exhausted)
            return Gtk.ResponseType.CANCEL
        with patch.object(Gtk.Dialog, 'run', cancel):
            detail.confirm_reset()
        self.assertEqual(calls, [], 'Cancel must not invoke reset callback')
        detail.window.destroy()

    def test_claude_has_colored_bars_but_no_manual_reset_button(self):
        data = json.loads((Path(__file__).resolve().parents[1] / 'tests' / 'fixtures' / 'claude_snapshot.json').read_text())
        detail = UsageDetails('Claude', 'anthropic', lambda: None, lambda _: self.fail('Claude reset must not run'))
        detail.update(data)
        self.assertFalse(detail.reset_button.get_visible())
        self.assertEqual(reset_credits(data), 0)
        detail.confirm_reset()
        detail.window.destroy()

if __name__ == '__main__':
    unittest.main()
