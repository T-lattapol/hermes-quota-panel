import unittest
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from usage_details import UsageDetails


def descendants(widget):
    yield widget
    if isinstance(widget, Gtk.Container):
        for child in widget.get_children():
            yield from descendants(child)


class ButtonEffectsTests(unittest.TestCase):
    def test_refresh_has_distinct_hover_and_pressed_feedback(self):
        detail = UsageDetails('Codex', 'openai-codex', lambda: None, lambda _: None)
        try:
            button = next(w for w in descendants(detail.window) if isinstance(w, Gtk.Button) and w.get_label() == 'Refresh')
            context = button.get_style_context()
            normal = context.get_background_color(Gtk.StateFlags.NORMAL).to_string()
            hover = context.get_background_color(Gtk.StateFlags.PRELIGHT).to_string()
            pressed = context.get_background_color(Gtk.StateFlags.ACTIVE).to_string()
            self.assertNotEqual(normal, hover, 'Hover must visibly change the button')
            self.assertNotEqual(normal, pressed, 'Press must visibly change the button')
            self.assertNotEqual(hover, pressed, 'Pressed feedback must differ from hover')
        finally:
            detail.window.destroy()


if __name__ == '__main__':
    unittest.main()
