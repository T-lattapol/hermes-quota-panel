"""Read-only account metadata for the panel's account selector.

Only labels/ids/priority ever leave this module — never a token, header, or
raw credential. The global credential pool's active/default account, its
priorities and cooldowns are never written here (read-only module).
"""
import unittest
from unittest.mock import patch

import account_selector as acc


def pool_entry(id, label, priority, auth_type='oauth', access_token='secret-token', **extra):
    entry = dict(id=id, label=label, priority=priority, auth_type=auth_type, **extra)
    if access_token is not None:
        entry['access_token'] = access_token
    return entry


class ListAccountsTests(unittest.TestCase):
    def test_lists_usable_oauth_entries_sorted_by_priority(self):
        entries = [pool_entry('b', 'second', 1), pool_entry('a', 'first', 0)]
        with patch('account_selector.read_credential_pool', return_value=entries):
            accounts = acc.list_accounts('anthropic')
        self.assertEqual([a['id'] for a in accounts], ['a', 'b'])
        self.assertEqual([a['label'] for a in accounts], ['first', 'second'])

    def test_skips_oauth_entries_without_a_usable_access_token(self):
        entries = [pool_entry('a', 'has-token', 0), pool_entry('b', 'no-token', 1, access_token=None)]
        with patch('account_selector.read_credential_pool', return_value=entries):
            accounts = acc.list_accounts('anthropic')
        self.assertEqual([a['id'] for a in accounts], ['a'])

    def test_skips_non_oauth_entries_and_falls_back_to_singleton(self):
        entries = [pool_entry('a', 'api-key', 0, auth_type='api_key')]
        with patch('account_selector.read_credential_pool', return_value=entries):
            accounts = acc.list_accounts('anthropic')
        self.assertEqual([a['id'] for a in accounts], ['default'])

    def test_marks_the_lowest_priority_entry_as_default(self):
        entries = [pool_entry('b', 'second', 1), pool_entry('a', 'first', 0)]
        with patch('account_selector.read_credential_pool', return_value=entries):
            accounts = acc.list_accounts('anthropic')
        flags = {a['id']: a['is_default'] for a in accounts}
        self.assertEqual(flags, {'a': True, 'b': False})

    def test_empty_pool_falls_back_to_a_singleton_pseudo_account(self):
        with patch('account_selector.read_credential_pool', return_value=[]):
            accounts = acc.list_accounts('openai-codex')
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]['id'], 'default')
        self.assertTrue(accounts[0]['is_default'])
        self.assertNotIn('access_token', accounts[0])

    def test_never_exposes_token_or_header_fields(self):
        entries = [pool_entry('a', 'first', 0, secret_fingerprint='abc', refresh_token='xyz')]
        with patch('account_selector.read_credential_pool', return_value=entries):
            accounts = acc.list_accounts('anthropic')
        for key in ('access_token', 'refresh_token', 'secret_fingerprint'):
            self.assertNotIn(key, accounts[0])


class DefaultAccountIdTests(unittest.TestCase):
    def test_default_is_the_lowest_priority_usable_entry(self):
        entries = [pool_entry('b', 'second', 5), pool_entry('a', 'first', 0)]
        with patch('account_selector.read_credential_pool', return_value=entries):
            self.assertEqual(acc.default_account_id('anthropic'), 'a')

    def test_default_is_the_singleton_when_pool_is_empty(self):
        with patch('account_selector.read_credential_pool', return_value=[]):
            self.assertEqual(acc.default_account_id('anthropic'), 'default')


class IsDefaultSelectionTests(unittest.TestCase):
    def test_none_and_default_marker_count_as_default(self):
        with patch('account_selector.read_credential_pool', return_value=[]):
            self.assertTrue(acc.is_default_selection('openai-codex', None))
            self.assertTrue(acc.is_default_selection('openai-codex', 'default'))

    def test_a_specific_non_default_pool_entry_is_not_default(self):
        entries = [pool_entry('b', 'second', 5), pool_entry('a', 'first', 0)]
        with patch('account_selector.read_credential_pool', return_value=entries):
            self.assertFalse(acc.is_default_selection('anthropic', 'b'))
            self.assertTrue(acc.is_default_selection('anthropic', 'a'))


if __name__ == '__main__':
    unittest.main()
