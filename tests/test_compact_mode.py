"""TDD: compact mode retains identity/selector/bars/toggle, hides the rest."""
import json
import unittest
from pathlib import Path

from usage_details import UsageDetails
from gi.repository import Gtk, GLib


def pump(seconds):
    GLib.timeout_add(max(1, int(seconds * 1000)), Gtk.main_quit)
    Gtk.main()


class CompactModeTests(unittest.TestCase):
    def _detail(self):
        detail = UsageDetails('Codex', 'openai-codex', lambda: None, lambda _: None, layout_path=None)
        detail.show()
        pump(.1)
        return detail

    def test_starts_in_full_mode_with_everything_visible(self):
        detail = self._detail()
        try:
            self.assertFalse(detail.compact)
            self.assertTrue(detail.account.get_visible())
            self.assertTrue(detail.status.get_visible())
        finally:
            detail.window.destroy()

    def test_compact_mode_hides_verbose_widgets_but_keeps_identity_selector_bars_and_toggle(self):
        detail = self._detail()
        try:
            detail.update(json.loads((Path(__file__).resolve().parents[1] / 'tests' / 'fixtures' / 'codex_snapshot.json').read_text()))
            detail.set_compact(True)
            self.assertTrue(detail.compact)
            # Retained: provider identity, account selector, both progress bars, mode toggle.
            self.assertTrue(detail.title.get_visible())
            self.assertTrue(detail.account_selector.get_visible())
            for _, (value, bar, _) in detail.rows.items():
                self.assertTrue(value.get_visible())
                self.assertTrue(bar.get_visible())
            self.assertTrue(detail.mode_toggle.get_visible())
            # Hidden: verbose dates/expiry/account details/reset controls.
            self.assertFalse(detail.account.get_visible())
            self.assertFalse(detail.status.get_visible())
            self.assertFalse(detail.expiry_label.get_visible())
            self.assertFalse(detail.reset_button.get_visible())
            self.assertFalse(detail.reset_note.get_visible())
            for _, (_, _, detail_label) in detail.rows.items():
                self.assertFalse(detail_label.get_visible())
        finally:
            detail.window.destroy()

    def test_switching_back_to_full_restores_everything_even_after_show_all(self):
        detail = self._detail()
        try:
            detail.update(json.loads((Path(__file__).resolve().parents[1] / 'tests' / 'fixtures' / 'codex_snapshot.json').read_text()))
            detail.set_compact(True)
            detail.set_compact(False)
            detail.window.show_all()
            self.assertFalse(detail.compact)
            self.assertTrue(detail.account.get_visible())
            self.assertTrue(detail.status.get_visible())
            self.assertTrue(detail.expiry_label.get_visible())  # Codex provider shows expiry when data present
            self.assertTrue(detail.reset_button.get_visible())
        finally:
            detail.window.destroy()

    def test_compact_survives_show_hide_show_cycle(self):
        detail = self._detail()
        try:
            detail.update(json.loads((Path(__file__).resolve().parents[1] / 'tests' / 'fixtures' / 'codex_snapshot.json').read_text()))
            detail.set_compact(True)
            detail.show()
            pump(.1)
            detail.hide()
            detail.show()
            pump(.1)
            self.assertTrue(detail.compact)
            self.assertFalse(detail.status.get_visible())
            self.assertTrue(detail.account_selector.get_visible())
        finally:
            detail.window.destroy()

    def test_claude_without_reset_support_keeps_reset_hidden_in_full_mode_after_toggle(self):
        detail = UsageDetails('Claude', 'anthropic', lambda: None, lambda _: None, layout_path=None)
        try:
            detail.update(json.loads((Path(__file__).resolve().parents[1] / 'tests' / 'fixtures' / 'claude_snapshot.json').read_text()))
            self.assertFalse(detail.reset_button.get_visible())
            detail.set_compact(True)
            detail.set_compact(False)
            self.assertFalse(detail.reset_button.get_visible(), 'Claude never shows a manual reset button')
        finally:
            detail.window.destroy()


class CompactUpdateTests(unittest.TestCase):
    def test_refresh_while_compact_does_not_restore_hidden_reset_and_dates(self):
        d = UsageDetails('Codex', 'openai-codex', lambda: None, lambda _: None)
        try:
            data = json.loads((Path(__file__).resolve().parents[1] / 'tests' / 'fixtures' / 'codex_snapshot.json').read_text())
            d.update(data)
            d.show()
            d.set_compact(True)
            d.update(data)
            self.assertFalse(d.reset_button.get_visible())
            self.assertFalse(d.expiry_label.get_visible())
            self.assertFalse(d.status.get_visible())
            self.assertFalse(d.reset_note.get_visible())
            for _, _, label in d.rows.values():
                self.assertFalse(label.get_visible())
        finally:
            d.window.destroy()


if __name__ == '__main__':
    unittest.main()
