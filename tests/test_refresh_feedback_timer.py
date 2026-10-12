import time
import unittest
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from usage_details import UsageDetails


def pump(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        time.sleep(.01)


class RefreshFeedbackTimerTests(unittest.TestCase):
    def test_success_checkmark_clears_after_short_delay(self):
        detail = UsageDetails('Codex', 'openai-codex', lambda: None, lambda _: None)
        try:
            detail.refresh_button.emit('clicked')
            detail.finish_refresh(True)
            self.assertEqual(detail.refresh_button.get_label(), 'Refresh ✓')
            pump(1.8)
            self.assertEqual(detail.refresh_button.get_label(), 'Refresh')
        finally:
            detail.window.destroy()

    def test_old_timer_does_not_clear_a_new_success_early(self):
        detail = UsageDetails('Codex', 'openai-codex', lambda: None, lambda _: None)
        try:
            detail.refresh_button.emit('clicked')
            detail.finish_refresh(True)
            pump(.7)
            detail.refresh_button.emit('clicked')
            detail.finish_refresh(True)
            pump(.9)
            self.assertEqual(detail.refresh_button.get_label(), 'Refresh ✓', 'Old timer must not erase the new success')
            pump(.8)
            self.assertEqual(detail.refresh_button.get_label(), 'Refresh')
        finally:
            detail.window.destroy()

    def test_destroy_cancels_pending_feedback_callback(self):
        from unittest.mock import Mock
        detail = UsageDetails('Codex', 'openai-codex', lambda: None, lambda _: None)
        detail.clear_refresh_feedback = Mock(wraps=detail.clear_refresh_feedback)
        detail.refresh_button.emit('clicked')
        detail.finish_refresh(True)
        detail.window.destroy()
        pump(1.8)
        detail.clear_refresh_feedback.assert_not_called()


if __name__ == '__main__':
    unittest.main()
