import ast
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]


class DesktopPresenceTests(unittest.TestCase):
    def test_detects_only_desktop_main_process_not_cli_or_electron_children(self):
        import desktop_presence
        with tempfile.TemporaryDirectory() as folder:
            proc = Path(folder)
            def process(pid, argv):
                path = proc / str(pid)
                path.mkdir(exist_ok=True)
                (path / 'cmdline').write_bytes(b'\0'.join(s.encode() for s in argv) + b'\0')
            process(1, ['/bin/python', '/opt/hermes', 'gateway'])
            process(2, ['/opt/Hermes', '--type=zygote'])
            process(3, ['/opt/chrome_crashpad_handler', '--annotation=_productName=Hermes'])
            self.assertFalse(desktop_presence.desktop_running(proc))
            process(4, ['/opt/Hermes', '--no-sandbox'])
            self.assertTrue(desktop_presence.desktop_running(proc))

    def test_gate_hides_details_blocks_refresh_and_resumes_without_popup(self):
        tree = ast.parse((ROOT / 'codex_panel.py').read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'CodexPanel')
        cls.body = [n for n in cls.body if not isinstance(n, ast.FunctionDef) or n.name != '__init__']
        statuses = Mock(ACTIVE='active', PASSIVE='passive')
        namespace = {'Indicator': Mock(IndicatorStatus=statuses), 'desktop_running': Mock(return_value=False)}
        exec(compile(ast.Module(body=[cls], type_ignores=[]), 'panel', 'exec'), namespace)
        panel = namespace['CodexPanel']()
        panel.indicator = Mock()
        panel.details = Mock()
        panel.visible_for_desktop = True
        panel.visibility_mode = 'desktop'
        panel.request_generation = 5
        panel.busy = True
        panel.resetting = False
        panel.latest_data = {'cached': True}
        panel.fetch = Mock()
        self.assertTrue(hasattr(panel, 'check_desktop_presence'), 'Missing desktop lifecycle gate')
        panel.check_desktop_presence()
        panel.indicator.set_status.assert_called_with('passive')
        panel.details.hide.assert_called_once()
        self.assertEqual(panel.request_generation, 6)
        self.assertIsNone(panel.latest_data)
        panel.refresh()
        panel.fetch.assert_not_called()
        panel.show_details()
        panel.details.show.assert_not_called()
        panel.refresh = Mock()
        namespace['desktop_running'].return_value = True
        panel.check_desktop_presence()
        panel.indicator.set_status.assert_called_with('active')
        panel.refresh.assert_called_once()
        panel.details.show.assert_not_called()
        panel.check_desktop_presence()
        panel.refresh.assert_called_once()

    def test_always_mode_ignores_desktop_absence(self):
        import desktop_presence
        self.assertTrue(desktop_presence.should_show('always', False))
        self.assertFalse(desktop_presence.should_show('desktop', False))
        self.assertTrue(desktop_presence.should_show('desktop', True))


class NativeLifecycleTests(unittest.TestCase):
    def test_native_indicator_hides_and_reappears_without_reopening_details(self):
        import gi
        gi.require_version('Gtk', '3.0')
        gi.require_version('AyatanaAppIndicator3', '0.1')
        from gi.repository import Gtk, GLib, Gio, AyatanaAppIndicator3 as Indicator
        from usage_details import UsageDetails
        from runtime_paths import APP_DIR
        import panel_geometry
        import os
        tree = ast.parse((ROOT / 'codex_panel.py').read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'CodexPanel')
        detector = Mock(return_value=True)
        with tempfile.TemporaryDirectory() as folder:
            namespace = dict(os=os, HOME=Path(folder), APP_DIR=APP_DIR, PROVIDER='openai-codex',
                             NAME='Codex', Indicator=Indicator, Gtk=Gtk, GLib=GLib, Gio=Gio,
                             panel_geometry=panel_geometry, desktop_running=detector)
            exec(compile(ast.Module(body=[cls], type_ignores=[]), 'panel', 'exec'), namespace)
            cls = namespace['CodexPanel']
            cls.load_accounts = lambda self: None
            cls.refresh = Mock(return_value=True)  # Never call quota APIs in a native lifecycle test.
            from unittest.mock import patch as mock_patch
            with mock_patch.object(GLib, 'timeout_add_seconds', return_value=0):
                panel = cls()
            panel.details = UsageDetails('Codex', 'openai-codex', lambda: None, lambda _: None)
            panel.details.show()
            self.assertTrue(panel.details.window.get_visible())
            detector.return_value = False
            panel.check_desktop_presence()
            self.assertEqual(panel.indicator.get_status(), Indicator.IndicatorStatus.PASSIVE)
            self.assertFalse(panel.details.window.get_visible())
            detector.return_value = True
            panel.check_desktop_presence()
            self.assertEqual(panel.indicator.get_status(), Indicator.IndicatorStatus.ACTIVE)
            self.assertFalse(panel.details.window.get_visible())
            self.assertEqual(cls.refresh.call_count, 2)
            panel.details.window.destroy()
            panel.bus.remove_filter(panel.bus_filter)
            panel.bus.signal_unsubscribe(panel.detail_signal)
            panel.bus.signal_unsubscribe(panel.hidden_signal)
            panel.indicator.set_status(Indicator.IndicatorStatus.PASSIVE)


if __name__ == '__main__':
    unittest.main()
