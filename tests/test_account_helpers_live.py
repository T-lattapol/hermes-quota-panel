"""Exercise the real --list-accounts / --account-id helper scripts via subprocess.

Only metadata assertions here (ids/labels) — no credential values are ever
printed by these scripts, and no reset credit is ever consumed by this test
(``codex_reset.py`` is only run WITHOUT --confirm, or with --confirm and a
non-default --account-id so the gate refuses before any network call).
"""
import json
import os
import subprocess
import unittest
from pathlib import Path

from runtime_paths import APP_DIR, HERMES_PYTHON, HELPER_ENV
VENV_PY = HERMES_PYTHON
WIDGET_DIR = str(APP_DIR)
ENV = HELPER_ENV


def run(script, *args):
    return subprocess.run([VENV_PY, str(Path(WIDGET_DIR) / script), *args],
                           cwd=WIDGET_DIR, env=ENV, capture_output=True, text=True, timeout=30)


@unittest.skipUnless(os.environ.get('RUN_LIVE_TESTS') == '1', 'Opt-in only: requires real Hermes OAuth accounts and makes network requests')
class ListAccountsHelperTests(unittest.TestCase):
    def test_claude_list_accounts_prints_only_safe_metadata(self):
        result = run('claude_usage.py', '--list-accounts')
        self.assertEqual(result.returncode, 0, result.stderr)
        accounts = json.loads(result.stdout)
        self.assertIsInstance(accounts, list)
        self.assertGreaterEqual(len(accounts), 1)
        for account in accounts:
            self.assertEqual(set(account) & {'access_token', 'refresh_token', 'secret_fingerprint'}, set())
            self.assertIn('id', account)
            self.assertIn('label', account)
            self.assertIn('is_default', account)

    def test_codex_list_accounts_prints_only_safe_metadata(self):
        result = run('codex_usage.py', '--list-accounts')
        self.assertEqual(result.returncode, 0, result.stderr)
        accounts = json.loads(result.stdout)
        self.assertIsInstance(accounts, list)
        self.assertGreaterEqual(len(accounts), 1)
        for account in accounts:
            self.assertEqual(set(account) & {'access_token', 'refresh_token', 'secret_fingerprint'}, set())

    def test_codex_usage_rejects_an_unknown_account_id_without_leaking_anything(self):
        result = run('codex_usage.py', '--account-id', 'not-a-real-id')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('access_token', result.stdout + result.stderr)

    def test_claude_usage_rejects_an_unknown_account_id(self):
        result = run('claude_usage.py', '--account-id', 'not-a-real-id')
        self.assertNotEqual(result.returncode, 0)

    def test_codex_usage_explicit_account_id_labels_and_echoes_the_requested_id(self):
        """An explicit (non-'default') Codex selection must report back the exact
        requested local account_id and an accurate, non-empty account_label — the
        parent diffs these against the request to reject a stale/raced result."""
        accounts = json.loads(run('codex_usage.py', '--list-accounts').stdout)
        account_id = accounts[0]['id']
        result = run('codex_usage.py', '--account-id', account_id)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['account_id'], account_id)
        self.assertEqual(data['account_label'], accounts[0]['label'])
        self.assertNotIn('access_token', result.stdout)

    def test_claude_usage_explicit_account_id_labels_and_echoes_the_requested_id(self):
        accounts = json.loads(run('claude_usage.py', '--list-accounts').stdout)
        account_id = accounts[0]['id']
        result = run('claude_usage.py', '--account-id', account_id)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['account_id'], account_id)
        self.assertEqual(data['account_label'], accounts[0]['label'])
        self.assertNotIn('access_token', result.stdout)

    def test_codex_reset_refuses_confirm_for_a_non_default_account_without_any_network_call(self):
        result = run('codex_reset.py', '--confirm', '--account-id', 'some-other-account-not-default')
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload['status'], 'skipped_non_default')
        self.assertFalse(payload['redeemed'])

    def test_codex_reset_dry_run_without_confirm_never_redeems(self):
        result = run('codex_reset.py')
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload['dry_run'])


if __name__ == '__main__':
    unittest.main()
