"""TDD: a shared geometry file keeps Codex and Claude windows at a common
position/size, re-reading the latest geometry every time a hidden window is
shown again (not just on first construction)."""
import json
import tempfile
import unittest
from pathlib import Path

from usage_details import UsageDetails
from gi.repository import Gtk, GLib


def pump(seconds):
    GLib.timeout_add(max(1, int(seconds * 1000)), Gtk.main_quit)
    Gtk.main()


class SharedGeometryHandoffTests(unittest.TestCase):
    def test_two_providers_pointed_at_the_same_file_share_position_and_size(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'shared.json'
            codex = UsageDetails('Codex', 'openai-codex', lambda: None, lambda _: None, layout_path=path)
            claude = UsageDetails('Claude', 'anthropic', lambda: None, lambda _: None, layout_path=path)
            try:
                codex.show()
                pump(.2)
                codex.window.move(133, 177)
                codex.window.resize(500, 460)
                pump(.4)
                codex.hide()
                # Claude must pick up Codex's geometry on its very first show.
                claude.show()
                pump(.2)
                self.assertEqual(tuple(claude.window.get_position()), (133, 177))
                self.assertEqual(tuple(claude.window.get_size()), (500, 460))
            finally:
                codex.window.destroy()
                claude.window.destroy()

    def test_reshowing_a_window_rereads_geometry_moved_by_the_other_provider_meanwhile(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'shared.json'
            codex = UsageDetails('Codex', 'openai-codex', lambda: None, lambda _: None, layout_path=path)
            claude = UsageDetails('Claude', 'anthropic', lambda: None, lambda _: None, layout_path=path)
            try:
                codex.show()
                pump(.2)
                codex.hide()
                claude.show()
                pump(.2)
                claude.window.move(200, 240)
                claude.window.resize(480, 420)
                pump(.4)
                claude.hide()
                # Codex was already shown once before (with stale geometry cached); showing it
                # again must re-read the file, not reuse what it saw the first time.
                codex.show()
                pump(.2)
                self.assertEqual(tuple(codex.window.get_position()), (200, 240))
                self.assertEqual(tuple(codex.window.get_size()), (480, 420))
            finally:
                codex.window.destroy()
                claude.window.destroy()

    def test_compact_and_full_geometry_are_tracked_independently_per_mode(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'shared.json'
            detail = UsageDetails('Codex', 'openai-codex', lambda: None, lambda _: None, layout_path=path)
            try:
                detail.show()
                pump(.2)
                detail.window.move(100, 100)
                detail.window.resize(500, 450)
                pump(.4)
                detail.set_compact(True)
                pump(.1)
                detail.window.move(900, 50)
                detail.window.resize(260, 160)
                pump(.4)
                detail.hide()
                detail.set_compact(False)
                detail.show()
                pump(.2)
                self.assertEqual(tuple(detail.window.get_position()), (100, 100))
                self.assertEqual(tuple(detail.window.get_size()), (500, 450))
            finally:
                detail.window.destroy()


if __name__ == '__main__':
    unittest.main()
