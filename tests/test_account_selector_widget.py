"""TDD: account selector widget — metadata-only labels, selection callback,
immediate clear-on-switch, and stale-fetch protection via request generation."""
import unittest
from unittest.mock import Mock

from usage_details import UsageDetails


class AccountSelectorWidgetTests(unittest.TestCase):
    def _detail(self, on_account_changed=None):
        return UsageDetails('Codex', 'openai-codex', lambda: None, lambda _: None,
                             layout_path=None, on_account_changed=on_account_changed)

    def test_set_accounts_populates_the_selector_with_labels_only(self):
        detail = self._detail()
        try:
            detail.set_accounts(
                [{'id': 'a', 'label': 'First account', 'is_default': True},
                 {'id': 'b', 'label': 'Second account', 'is_default': False}], selected_id='a')
            self.assertEqual(detail.account_selector.get_active_id(), 'a')
            model = detail.account_selector.get_model()
            texts = [row[0] for row in model]
            self.assertEqual(texts, ['First account', 'Second account'])
        finally:
            detail.window.destroy()

    def test_choosing_a_different_account_fires_the_callback_with_its_id(self):
        calls = []
        detail = self._detail(on_account_changed=calls.append)
        try:
            detail.set_accounts(
                [{'id': 'a', 'label': 'First', 'is_default': True},
                 {'id': 'b', 'label': 'Second', 'is_default': False}], selected_id='a')
            detail.account_selector.set_active_id('b')
            self.assertEqual(calls, ['b'])
        finally:
            detail.window.destroy()

    def test_selecting_an_account_clears_the_displayed_quota_immediately(self):
        detail = self._detail(on_account_changed=lambda _id: None)
        try:
            detail.update({'provider': 'openai-codex', 'fetched_at': '2026-01-01T00:00:00+00:00',
                            'windows': [{'label': 'Session', 'used_percent': 80, 'resets_at': None},
                                        {'label': 'Weekly', 'used_percent': 40, 'resets_at': None}],
                            'account_label': 'Old account'})
            detail.set_accounts(
                [{'id': 'a', 'label': 'First', 'is_default': True},
                 {'id': 'b', 'label': 'Second', 'is_default': False}], selected_id='a')
            detail.account_selector.set_active_id('b')
            value, bar, _ = detail.rows['Session']
            self.assertEqual(value.get_text(), 'Unavailable')
            self.assertEqual(bar.get_fraction(), 0)
        finally:
            detail.window.destroy()

    def test_programmatic_set_accounts_does_not_refire_the_changed_callback(self):
        calls = []
        detail = self._detail(on_account_changed=calls.append)
        try:
            detail.set_accounts(
                [{'id': 'a', 'label': 'First', 'is_default': True}], selected_id='a')
            detail.set_accounts(
                [{'id': 'a', 'label': 'First', 'is_default': True},
                 {'id': 'b', 'label': 'Second', 'is_default': False}], selected_id='a')
            self.assertEqual(calls, [])
        finally:
            detail.window.destroy()


if __name__ == '__main__':
    unittest.main()
