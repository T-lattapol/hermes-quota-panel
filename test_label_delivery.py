"""A constant quota must still notify a late-attaching GNOME indicator."""
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock
from gi.repository import GLib
from test_panel_toggle import panel_class


class LabelDeliveryTests(unittest.TestCase):
    def test_unchanged_snapshot_reannounces_ayatana_label(self):
        cls = panel_class()
        with tempfile.TemporaryDirectory() as directory:
            cls.apply.__globals__.update(NAME='Codex', PROVIDER='openai-codex', HOME=Path(directory), GLib=GLib, json=json)
            panel = cls()
            panel.details = None
            panel.indicator = Mock()
            panel.bus = Mock()
            panel.menu_path = '/org/ayatana/NotificationItem/codex_quota/Menu'
            fixture = {'windows': [{'label': 'Session', 'used_percent': 45}, {'label': 'Weekly', 'used_percent': 12}]}
            panel.apply(fixture)
            panel.bus.reset_mock()
            # Shell attaches after the initial signal; another equal snapshot must heal it.
            panel.apply(fixture)
            self.assertEqual(panel.bus.emit_signal.call_count, 1, 'No label notification for an unchanged quota')
            destination, path, interface, signal, payload = panel.bus.emit_signal.call_args.args
            self.assertIsNone(destination)
            self.assertEqual(path, '/org/ayatana/NotificationItem/codex_quota')
            self.assertEqual(interface, 'org.kde.StatusNotifierItem')
            self.assertEqual(signal, 'XAyatanaNewLabel')
            self.assertEqual(payload.unpack(), ('Codex 45% | W 12%', 'Codex 100% | W 100%'))


if __name__ == '__main__':
    unittest.main()
