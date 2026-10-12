import importlib.util
import unittest

class UsageUITests(unittest.TestCase):
    def test_progress_bar_represents_used_percentage(self):
        self.assertIsNotNone(importlib.util.find_spec('quota_ui'), 'Quota bar formatter is not implemented')
        from quota_ui import usage_bar
        self.assertEqual(usage_bar(50), '▰▰▰▰▰▰▰▰▰▰▱▱▱▱▱▱▱▱▱▱  50% used')
        self.assertEqual(usage_bar(0).count('▰'), 0)
        self.assertEqual(usage_bar(100).count('▰'), 20)

    def test_small_nonzero_usage_has_a_visible_segment(self):
        from quota_ui import usage_bar
        self.assertEqual(usage_bar(2).count('▰'), 1)

    def test_usage_bar_color_changes_with_usage(self):
        import quota_ui
        self.assertTrue(hasattr(quota_ui, 'usage_color'), 'Colored usage bars are missing')
        self.assertEqual(quota_ui.usage_color(20), 'green')
        self.assertEqual(quota_ui.usage_color(75), 'amber')
        self.assertEqual(quota_ui.usage_color(95), 'red')

    def test_reset_credit_count_only_enables_codex_with_banked_credits(self):
        import quota_ui
        self.assertTrue(hasattr(quota_ui, 'reset_credits'), 'Reset credit detection is missing')
        data = {'provider': 'openai-codex', 'details': ['You have 2 resets banked - use /usage reset to activate']}
        self.assertEqual(quota_ui.reset_credits(data), 2)
        self.assertEqual(quota_ui.reset_credits({**data, 'provider': 'anthropic'}), 0)
        self.assertEqual(quota_ui.reset_credits({'provider': 'openai-codex', 'details': []}), 0)

    def test_reset_expiry_uses_thailand_date_not_utc(self):
        import quota_ui
        self.assertTrue(hasattr(quota_ui, 'reset_expiry_lines'), 'Reset credit expiry display is missing')
        data = {'provider': 'openai-codex', 'reset_credit_details': [
            {'status': 'available', 'expires_at': '2030-01-01T00:00:00Z'},
            {'status': 'available', 'expires_at': '2030-01-02T12:00:00Z'}]}
        self.assertEqual(quota_ui.reset_expiry_lines(data), [
            'Reset 1 expires 01 Jan 2030 · 07:00 ICT',
            'Reset 2 expires 02 Jan 2030 · 19:00 ICT'])

    def test_direct_click_matches_only_root_menu_open_event(self):
        import quota_ui
        self.assertTrue(hasattr(quota_ui, 'is_menu_open_event'), 'Direct click handler is missing')
        self.assertTrue(quota_ui.is_menu_open_event((0, 'opened', None, 0)))
        self.assertFalse(quota_ui.is_menu_open_event((0, 'closed', None, 0)))
        self.assertFalse(quota_ui.is_menu_open_event((2, 'clicked', None, 0)))

    def test_tray_menu_has_no_duplicate_monochrome_usage_rows(self):
        import ast
        from pathlib import Path
        source = ast.parse((Path(__file__).resolve().parents[1] / 'codex_panel.py').read_text())
        cls = next(node for node in source.body if isinstance(node, ast.ClassDef) and node.name == 'CodexPanel')
        init = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == '__init__')
        captions = [node.args[0].value for node in ast.walk(init)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'item' and node.args and isinstance(node.args[0], ast.Constant)]
        self.assertEqual(captions, ['Usage details…', 'Quit'])

if __name__ == '__main__':
    unittest.main()
