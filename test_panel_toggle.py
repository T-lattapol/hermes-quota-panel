"""Exercise the real panel methods without credentials or indicator startup."""
import ast
from pathlib import Path
import unittest
from unittest.mock import Mock


def panel_class():
    tree = ast.parse(Path(__file__).with_name('codex_panel.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'CodexPanel')
    cls.body = [n for n in cls.body if not isinstance(n, ast.FunctionDef) or n.name != '__init__']
    from runtime_paths import APP_DIR, HERMES_PYTHON, HELPER_ENV
    namespace = dict(APP_DIR=APP_DIR, HERMES_PYTHON=HERMES_PYTHON, HELPER_ENV=HELPER_ENV)
    exec(compile(ast.Module(body=[cls], type_ignores=[]), 'codex_panel.py', 'exec'), namespace)
    return namespace['CodexPanel']


class ToggleTests(unittest.TestCase):
    def test_second_click_hides_then_third_click_reopens(self):
        cls = panel_class()
        self.assertTrue(hasattr(cls, 'toggle_details'), 'Panel has no repeated-click toggle')
        for provider in ('openai-codex', 'anthropic'):
            with self.subTest(provider=provider):
                panel = cls()
                visible = [False]
                panel.details = Mock()
                panel.details.window.get_visible.side_effect = lambda: visible[0]
                panel.details.hide.side_effect = lambda: visible.__setitem__(0, False)
                panel.show_details = Mock(side_effect=lambda: visible.__setitem__(0, True))
                self.assertFalse(panel.toggle_details())
                self.assertTrue(visible[0])
                self.assertFalse(panel.toggle_details())
                self.assertFalse(visible[0])
                self.assertFalse(panel.toggle_details())
                self.assertTrue(visible[0])
                self.assertEqual(panel.show_details.call_count, 2)
                panel.details.hide.assert_called_once()


if __name__ == '__main__':
    unittest.main()
