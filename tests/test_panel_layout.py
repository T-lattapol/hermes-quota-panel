import json
import tempfile
import unittest
from pathlib import Path
from usage_details import UsageDetails
from gi.repository import Gtk, GLib


def pump(seconds):
    # A real GTK loop is needed for frame-clock-driven scrolled-window resizing.
    GLib.timeout_add(max(1, int(seconds * 1000)), Gtk.main_quit)
    Gtk.main()



class PanelLayoutTests(unittest.TestCase):
    def test_panel_can_be_resized(self):
        detail = UsageDetails('Codex', 'openai-codex', lambda: None, lambda _: None)
        try:
            self.assertTrue(detail.window.get_resizable())
        finally:
            detail.window.destroy()

    def test_move_and_size_are_saved_and_reused_after_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'layout.json'
            detail = UsageDetails('Codex', 'openai-codex', lambda: None, lambda _: None)
            detail.layout_path = path
            try:
                detail.show()
                pump(.2)
                detail.window.move(120, 180)
                detail.window.resize(600, 620)
                pump(.3)
                position, size = tuple(detail.window.get_position()), tuple(detail.window.get_size())
                detail.hide()
                self.assertTrue(path.exists(), 'Hiding must persist the panel geometry')
                saved = json.loads(path.read_text())
                self.assertEqual((saved['x'], saved['y']), position)
                self.assertEqual((saved['width'], saved['height']), size)
                detail.show()
                pump(.2)
                self.assertEqual(tuple(detail.window.get_position()), position)
                self.assertEqual(tuple(detail.window.get_size()), size)
            finally:
                detail.window.destroy()

    def test_new_instance_restores_persisted_layout(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'layout.json'
            saved = dict(x=140, y=190, width=610, height=630)
            path.write_text(json.dumps(saved))
            detail = UsageDetails('Codex', 'openai-codex', lambda: None, lambda _: None, layout_path=path)
            try:
                detail.show()
                pump(.3)
                self.assertEqual(tuple(detail.window.get_position()), (140, 190))
                self.assertEqual(tuple(detail.window.get_size()), (610, 630))
            finally:
                detail.window.destroy()

    def test_geometry_is_saved_while_panel_is_still_open(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'layout.json'
            detail = UsageDetails('Codex', 'openai-codex', lambda: None, lambda _: None, layout_path=path)
            try:
                detail.show()
                pump(.2)
                detail.window.move(170, 230)
                detail.window.resize(640, 660)
                pump(.7)
                self.assertTrue(path.exists(), 'Moving must save without requiring close')
                saved = json.loads(path.read_text())
                self.assertEqual((saved['x'], saved['y']), tuple(detail.window.get_position()))
                self.assertEqual((saved['width'], saved['height']), tuple(detail.window.get_size()))
            finally:
                detail.window.destroy()

    def test_disconnected_monitor_layout_is_clamped_to_a_visible_screen(self):
        from gi.repository import Gdk
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'layout.json'
            path.write_text(json.dumps(dict(x=-20000, y=-20000, width=610, height=630)))
            detail = UsageDetails('Codex', 'openai-codex', lambda: None, lambda _: None, layout_path=path)
            try:
                self.assertTrue(detail.restore_layout())
                x, y = detail.window.get_position()
                display = Gdk.Display.get_default()
                areas = [display.get_monitor(i).get_workarea() for i in range(display.get_n_monitors())]
                self.assertTrue(any(r.x <= x < r.x + r.width and r.y <= y < r.y + r.height for r in areas), 'Restore must not leave the panel off-screen')
            finally:
                detail.window.destroy()

    def test_panel_can_shrink_without_losing_content(self):
        from gi.repository import Gtk
        detail = UsageDetails('Codex', 'openai-codex', lambda: None, lambda _: None)
        try:
            detail.update(json.loads((Path(__file__).resolve().parents[1] / 'tests' / 'fixtures' / 'codex_snapshot.json').read_text()))
            detail.show()
            pump(.2)
            detail.window.resize(440, 280)
            pump(.3)
            self.assertLessEqual(detail.window.get_size().height, 300, 'Panel body must be scrollable when reduced')
            self.assertIsInstance(detail.window.get_child(), Gtk.ScrolledWindow)
        finally:
            detail.window.destroy()


if __name__ == '__main__':
    unittest.main()
