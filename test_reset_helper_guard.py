"""The reset CLI must reject EVERY explicit account, not guess pool defaults."""
import contextlib
import io
import runpy
import sys
import types
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import Mock, patch


@dataclass
class FakeResult:
    redeemed: bool = False


class ResetHelperGuardTests(unittest.TestCase):
    def test_first_pool_entry_cannot_authorize_ambient_reset_for_an_explicit_id(self):
        usage = types.ModuleType('agent.account_usage')
        usage.fetch_account_usage = Mock()
        usage.redeem_codex_reset_credit = Mock(return_value=FakeResult())
        commands = types.ModuleType('hermes_cli.subcommands.usage')
        commands.usage_snapshot_document = Mock()
        modules = {'agent': types.ModuleType('agent'), 'agent.account_usage': usage,
                   'hermes_cli': types.ModuleType('hermes_cli'), 'hermes_cli.subcommands': types.ModuleType('hermes_cli.subcommands'),
                   'hermes_cli.subcommands.usage': commands}
        with patch.dict(sys.modules, modules), patch('account_selector.is_default_selection', return_value=True), \
             patch.object(sys, 'argv', ['codex_reset.py', '--confirm', '--account-id', 'first-pool-entry']), \
             contextlib.redirect_stdout(io.StringIO()):
            try:
                runpy.run_path(str(Path(__file__).resolve().parent / 'codex_reset.py'), run_name='__main__')
            except SystemExit as error:
                self.assertEqual(error.code, 0)
        usage.redeem_codex_reset_credit.assert_not_called()
        usage.fetch_account_usage.assert_not_called()


if __name__ == '__main__':
    unittest.main()
