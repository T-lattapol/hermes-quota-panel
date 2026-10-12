import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock
import panel_geometry
from test_panel_toggle import panel_class


class AccountControllerTests(TestCase):
    def test_selection_clears_old_data_and_requests_the_selected_account(self):
        cls = panel_class()
        self.assertTrue(hasattr(cls, 'select_account'), 'Controller has not connected account selection')
        with tempfile.TemporaryDirectory() as directory:
            cls.select_account.__globals__.update(HOME=Path(directory), PROVIDER='anthropic', NAME='Claude', panel_geometry=panel_geometry)
            panel = cls()
            panel.available_accounts = [{'id': 'default', 'label': 'Default'}, {'id': 'second', 'label': 'Second'}]
            panel.selected_account_id = 'default'
            panel.request_generation = 4
            panel.latest_data = {'old': True}
            panel.busy = True
            panel.resetting = False
            panel.details = Mock()
            panel.publish_label = Mock()
            panel.refresh = Mock()
            panel.select_account('second')
            self.assertEqual(panel.selected_account_id, 'second')
            self.assertIsNone(panel.latest_data)
            self.assertFalse(panel.busy)
            self.assertGreater(panel.request_generation, 4)
            panel.details.clear_for_account_switch.assert_called_once()
            panel.refresh.assert_called_once()

    def test_loading_accounts_restores_only_widget_preference(self):
        import json, os
        cls = panel_class()
        self.assertTrue(hasattr(cls, 'load_accounts'), 'Account list has not been wired to the helper')
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / 'account_preferences.json').write_text(json.dumps({'anthropic': 'second'}))
            subprocess = Mock()
            subprocess.run.return_value.returncode = 0
            subprocess.run.return_value.stdout = json.dumps([{'id': 'second', 'label': 'Second'}])
            cls.load_accounts.__globals__.update(HOME=home, PROVIDER='anthropic', subprocess=subprocess, json=json, os=os)
            panel = cls()
            panel.load_accounts()
            self.assertEqual(panel.selected_account_id, 'second')
            self.assertEqual([item['id'] for item in panel.available_accounts], ['default', 'second'])
            self.assertIn('--list-accounts', subprocess.run.call_args.args[0])

    def test_old_snapshot_cannot_overwrite_new_account_or_busy_state(self):
        import inspect
        cls = panel_class()
        self.assertIn('generation', inspect.signature(cls.apply).parameters, 'Snapshot application must track the originating request')
        panel = cls()
        panel.request_generation = 8
        panel.busy = True
        panel.latest_data = {'new_account': True}
        panel.apply({'old_account': True}, generation=7)
        self.assertTrue(panel.busy)
        self.assertEqual(panel.latest_data, {'new_account': True})

    def test_fetch_passes_the_chosen_id_and_its_generation_to_apply(self):
        import inspect, json, os
        cls = panel_class()
        self.assertIn('generation', inspect.signature(cls.fetch).parameters, 'Fetch must capture account and request generation')
        with tempfile.TemporaryDirectory() as directory:
            subprocess = Mock()
            subprocess.run.return_value.returncode = 0
            subprocess.run.return_value.stdout = json.dumps({'windows': [{'label': 'Session', 'used_percent': 10}, {'label': 'Weekly', 'used_percent': 20}]})
            glib = Mock()
            cls.fetch.__globals__.update(HOME=Path(directory), PROVIDER='anthropic', subprocess=subprocess, json=json, os=os, GLib=glib)
            panel = cls()
            panel.fetch(12, 'second')
            command = subprocess.run.call_args.args[0]
            self.assertEqual(command[-2:], ['--account-id', 'second'])
            self.assertEqual(glib.idle_add.call_args.args[-1], 12)
            self.assertEqual(glib.idle_add.call_args.args[0], panel.apply)

    def test_old_failure_cannot_clear_the_new_accounts_snapshot(self):
        import inspect
        cls = panel_class()
        self.assertIn('generation', inspect.signature(cls.failed).parameters)
        panel = cls()
        panel.request_generation = 8
        panel.busy = True
        panel.latest_data = {'new_account': True}
        panel.failed('Expired old account', generation=7)
        self.assertTrue(panel.busy)
        self.assertEqual(panel.latest_data, {'new_account': True})

    def test_reset_controller_rejects_non_default_selection(self):
        cls = panel_class()
        cls.reset_usage.__globals__.update(PROVIDER='openai-codex', reset_credits=lambda _: 2)
        panel = cls()
        panel.resetting = False
        panel.latest_data = {'reset_allowed': True}
        panel.selected_account_id = 'other-account'
        panel.reset_usage()
        self.assertFalse(panel.resetting)

    def test_show_details_wires_shared_layout_and_account_selector(self):
        cls = panel_class()
        Details = Mock()
        with tempfile.TemporaryDirectory() as directory:
            cls.show_details.__globals__.update(HOME=Path(directory), PROVIDER='anthropic', NAME='Claude', UsageDetails=Details, GLib=Mock())
            panel = cls()
            panel.bus = Mock()
            panel.details = None
            panel.latest_data = None
            panel.available_accounts = [{'id': 'default', 'label': 'Default'}]
            panel.selected_account_id = 'default'
            panel.show_details()
            kwargs = Details.call_args.kwargs
            self.assertEqual(kwargs['layout_path'], Path(directory) / 'shared_panel_layout.json')
            self.assertEqual(kwargs['on_account_changed'], panel.select_account)
            Details.return_value.set_accounts.assert_called_once_with(panel.available_accounts, 'default')

    def test_incoming_provider_restores_after_outgoing_save(self):
        cls = panel_class()
        cls.on_details_shown.__globals__.update(PROVIDER='anthropic')
        panel = cls()
        panel.details = Mock()
        panel.details.window.get_visible.return_value = True
        panel.on_details_shown(None, None, None, None, None, Mock(unpack=lambda: ('openai-codex',)), None)
        panel.details.hide.assert_called_once()
        self.assertTrue(hasattr(panel, 'on_details_hidden'), 'Incoming panel needs a post-save geometry handoff signal')

    def test_pool_default_account_is_not_listed_twice(self):
        import json, os
        cls = panel_class()
        with tempfile.TemporaryDirectory() as directory:
            subprocess = Mock()
            subprocess.run.return_value.returncode = 0
            subprocess.run.return_value.stdout = json.dumps([
                {'id': 'main', 'label': 'oauth-6', 'is_default': True},
                {'id': 'spare', 'label': 'oauth-7', 'is_default': False}])
            cls.load_accounts.__globals__.update(HOME=Path(directory), PROVIDER='anthropic', subprocess=subprocess, json=json, os=os)
            panel = cls()
            panel.load_accounts()
            self.assertEqual(panel.available_accounts, [
                {'id': 'default', 'label': 'oauth-6 (default)'}, {'id': 'spare', 'label': 'oauth-7'}])

    def test_selector_is_disabled_during_reset_and_reenabled_after_result(self):
        from unittest.mock import call
        cls = panel_class()
        cls.reset_usage.__globals__.update(PROVIDER='openai-codex', reset_credits=lambda _: 2,
                                          threading=Mock(), Gtk=Mock())
        panel = cls()
        panel.resetting = False
        panel.selected_account_id = 'default'
        panel.latest_data = {'reset_allowed': True}
        panel.details = Mock()
        panel.refresh = Mock()
        panel.reset_usage()
        panel.reset_finished({'status': 'unavailable', 'message': 'Unit-test result; no credit consumed'})
        self.assertEqual(panel.details.account_selector.set_sensitive.call_args_list, [call(False), call(True)])

    def test_all_codex_pool_entries_are_selectable_even_if_first_is_marked_default(self):
        import json, os
        cls = panel_class()
        with tempfile.TemporaryDirectory() as directory:
            subprocess = Mock()
            subprocess.run.return_value.returncode = 0
            subprocess.run.return_value.stdout = json.dumps([
                {'id': 'main', 'label': 'Main', 'is_default': True},
                {'id': 'spare', 'label': 'Spare', 'is_default': False}])
            cls.load_accounts.__globals__.update(HOME=Path(directory), PROVIDER='openai-codex', subprocess=subprocess, json=json, os=os)
            panel = cls()
            panel.load_accounts()
            self.assertEqual([item['id'] for item in panel.available_accounts], ['default', 'main', 'spare'])
            self.assertEqual(panel.available_accounts[0]['label'], 'Default account (current login)')


if __name__ == '__main__':
    import unittest
    unittest.main()
