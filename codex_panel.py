#!/usr/bin/python3
"""Read-only Codex account quota indicator for Ubuntu's top panel."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import threading
import sys
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import Gtk, GLib, Gio, AyatanaAppIndicator3 as Indicator
from quota_ui import reset_credits, is_menu_open_event
from usage_details import UsageDetails
import panel_geometry
from desktop_presence import desktop_running
from runtime_paths import APP_DIR, STATE_DIR, HERMES_PYTHON, HELPER_ENV

HOME = STATE_DIR
HOME.mkdir(parents=True, exist_ok=True, mode=0o700)
PROVIDER = 'anthropic' if '--claude' in sys.argv else 'openai-codex'
NAME = 'Claude' if PROVIDER == 'anthropic' else 'Codex'
LOCK = open(HOME / ('claude_panel.lock' if PROVIDER == 'anthropic' else 'panel.lock'), 'w')
try:
    fcntl.flock(LOCK, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    raise SystemExit('Codex panel is already running')

class CodexPanel:
    def __init__(self):
        self.visibility_mode = os.environ.get('QUOTA_PANEL_VISIBILITY', 'desktop')
        self.visible_for_desktop = None
        self.busy = False
        self.resetting = False
        self.latest_data = None
        self.details = None
        self.request_generation = 0
        panel_geometry.migrate_legacy(HOME / 'shared_panel_layout.json', [HOME / 'panel_layout.json', HOME / 'claude_panel_layout.json'])
        self.load_accounts()
        self.indicator = Indicator.Indicator.new(
            'claude-quota' if PROVIDER == 'anthropic' else 'codex-quota', str(APP_DIR / 'icons' / ('claude.svg' if PROVIDER == 'anthropic' else 'openai.svg')),
            Indicator.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_title(NAME + ' quota')
        self.indicator.set_status(Indicator.IndicatorStatus.PASSIVE)
        self.indicator.set_label(NAME + ' …', NAME + ' 100% | W 100%')
        self.menu = Gtk.Menu()
        dashboard = self.item('Usage details…', True)
        dashboard.connect('activate', lambda _: self.show_details())
        quit_item = self.item('Quit', True)
        quit_item.connect('activate', lambda _: Gtk.main_quit())
        self.menu.show_all()
        self.indicator.set_menu(self.menu)
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.menu_path = '/org/ayatana/NotificationItem/' + ('claude_quota' if PROVIDER == 'anthropic' else 'codex_quota') + '/Menu'
        self.bus_filter = self.bus.add_filter(self.on_bus_message, None)
        self.detail_signal = self.bus.signal_subscribe(None, 'com.hermes.QuotaDetails', 'Shown', '/com/hermes/QuotaDetails', None, Gio.DBusSignalFlags.NONE, self.on_details_shown, None)
        self.hidden_signal = self.bus.signal_subscribe(None, 'com.hermes.QuotaDetails', 'Hidden', '/com/hermes/QuotaDetails', None, Gio.DBusSignalFlags.NONE, self.on_details_hidden, None)
        self.check_desktop_presence()
        GLib.timeout_add_seconds(3, self.check_desktop_presence)
        GLib.timeout_add_seconds(60, self.refresh)

    def item(self, label, enabled=False):
        item = Gtk.MenuItem(label=label)
        item.set_sensitive(enabled)
        self.menu.append(item)
        return item

    def load_accounts(self):
        self.available_accounts = [{'id': 'default', 'label': 'Default account (current login)'}]
        try:
            result = subprocess.run(
                [HERMES_PYTHON,
                 str(APP_DIR / ('claude_usage.py' if PROVIDER == 'anthropic' else 'codex_usage.py')),
                 '--list-accounts'], capture_output=True, text=True, timeout=15,
                env=HELPER_ENV)
            if result.returncode:
                raise RuntimeError('Account metadata unavailable')
            accounts = json.loads(result.stdout)
            for account in accounts:
                if not (isinstance(account, dict) and isinstance(account.get('id'), str) and isinstance(account.get('label'), str)):
                    continue
                if account.get('is_default') is True and PROVIDER == 'anthropic':
                    # Claude's helper explicitly uses this highest-priority pool entry.
                    # Codex's ambient resolver can use a singleton or a different pool entry,
                    # so keep every explicit Codex credential selectable instead of guessing.
                    self.available_accounts[0]['label'] = account['label'] + ' (default)'
                elif account['id'] != 'default':
                    self.available_accounts.append({'id': account['id'], 'label': account['label']})
        except (OSError, ValueError, TypeError, RuntimeError, subprocess.TimeoutExpired):
            print('Account metadata unavailable; keeping the default account', flush=True)
        try:
            selected = json.loads((HOME / 'account_preferences.json').read_text()).get(PROVIDER, 'default')
        except (OSError, ValueError, AttributeError):
            selected = 'default'
        self.selected_account_id = selected if selected in {a['id'] for a in self.available_accounts} else 'default'

    def select_account(self, account_id):
        if self.resetting or account_id == self.selected_account_id:
            return
        if account_id not in {account['id'] for account in self.available_accounts}:
            return
        self.selected_account_id = account_id
        self.request_generation += 1  # Invalidate the previous account's in-flight reply.
        self.busy = False
        self.latest_data = None
        if self.details:
            self.details.clear_for_account_switch()
        self.publish_label(NAME + ' switching…')
        panel_geometry._locked_merge_write(HOME / 'account_preferences.json',
                                          lambda document: document.__setitem__(PROVIDER, account_id))
        self.refresh()

    def check_desktop_presence(self):
        active = self.visibility_mode == 'always' or desktop_running()
        if active == self.visible_for_desktop:
            return True
        self.visible_for_desktop = active
        self.indicator.set_status(Indicator.IndicatorStatus.ACTIVE if active else Indicator.IndicatorStatus.PASSIVE)
        if active:
            self.refresh()  # Refresh on reopen; never automatically open details.
        else:
            self.request_generation += 1  # Discard an already-running quota reply.
            self.busy = False
            self.latest_data = None
            if self.details:
                self.details.hide()
        return True

    def refresh(self):
        if getattr(self, 'visible_for_desktop', True) is False:
            return True
        if not self.busy and not self.resetting:
            self.busy = True
            self.request_generation += 1
            threading.Thread(target=self.fetch, args=(self.request_generation, self.selected_account_id), daemon=True).start()
        return True

    def on_bus_message(self, connection, message, incoming, user_data):
        if (incoming and message.get_message_type() == Gio.DBusMessageType.METHOD_CALL
                and message.get_path() == self.menu_path
                and message.get_interface() == 'com.canonical.dbusmenu'
                and message.get_member() == 'Event'):
            body = message.get_body()
            if body is not None and is_menu_open_event(body.unpack()):
                GLib.idle_add(self.toggle_details)
        return message

    def on_details_shown(self, connection, sender, path, interface, signal, parameters, user_data):
        incoming = parameters.unpack()[0]
        if incoming != PROVIDER and self.details and self.details.window.get_visible():
            self.details.hide()  # hide() flushes current geometry to the shared file.
            if getattr(self, 'bus', None):
                self.bus.emit_signal(None, '/com/hermes/QuotaDetails', 'com.hermes.QuotaDetails',
                                     'Hidden', GLib.Variant('(s)', (incoming,)))

    def on_details_hidden(self, connection, sender, path, interface, signal, parameters, user_data):
        # The outgoing panel has saved; re-read geometry it may have written after we showed.
        if parameters.unpack()[0] == PROVIDER and self.details and self.details.window.get_visible():
            self.details.restore_layout()

    def toggle_details(self):
        if self.details is not None and self.details.window.get_visible():
            self.details.hide()
        else:
            self.show_details()
        return False

    def show_details(self):
        if getattr(self, 'visible_for_desktop', True) is False:
            return False
        self.bus.emit_signal(None, '/com/hermes/QuotaDetails', 'com.hermes.QuotaDetails', 'Shown', GLib.Variant('(s)', (PROVIDER,)))
        if self.details is None:
            self.details = UsageDetails(NAME, PROVIDER, self.refresh, self.reset_usage,
                                        layout_path=HOME / 'shared_panel_layout.json',
                                        on_account_changed=self.select_account)
            self.details.set_accounts(self.available_accounts, self.selected_account_id)
        if self.latest_data:
            self.details.update(self.latest_data, refresh_complete=False)
        self.details.show()
        return False

    def confirm_reset(self):
        self.show_details()
        if not self.resetting:
            self.details.confirm_reset()

    def reset_usage(self, force=False):
        if PROVIDER != 'openai-codex' or self.resetting or getattr(self, 'selected_account_id', 'default') != 'default':
            return
        if (self.latest_data or {}).get('reset_allowed') is not True or not reset_credits(self.latest_data or {}):
            return
        self.resetting = True
        if self.details:
            self.details.account_selector.set_sensitive(False)
        threading.Thread(target=self.reset_worker, args=(force,), daemon=True).start()

    def reset_worker(self, force):
        try:
            command = [HERMES_PYTHON, str(APP_DIR / 'codex_reset.py'), '--confirm']
            if force:
                command.append('--force')
            result = subprocess.run(command, capture_output=True, text=True, timeout=60,
                                    env=HELPER_ENV)
            if result.returncode:
                raise RuntimeError('Reset request failed; no automatic retry')
            outcome = json.loads(result.stdout)
        except Exception:
            outcome = {'status': 'unavailable', 'message': 'Reset result could not be confirmed. Refresh usage before trying again.'}
        GLib.idle_add(self.reset_finished, outcome)

    def reset_finished(self, outcome):
        self.resetting = False
        if self.details:
            self.details.account_selector.set_sensitive(True)
        verified = outcome.get('verified_usage')
        if verified:
            self.apply(verified)
        self.refresh()
        message = outcome.get('message', 'Reset request finished')
        if outcome.get('status') == 'reset' and not verified:
            message += '\nThe provider reported a reset, but usage read-back is unavailable.'
        dialog = Gtk.MessageDialog(transient_for=self.details.window if self.details else None,
                                   modal=True, message_type=Gtk.MessageType.INFO,
                                   buttons=Gtk.ButtonsType.CLOSE, text='Codex reset result')
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()
        return False

    def fetch(self, generation, account_id):
        try:
            result = subprocess.run(
                [HERMES_PYTHON, str(APP_DIR / ('claude_usage.py' if PROVIDER == 'anthropic' else 'codex_usage.py')), '--account-id', account_id],
                capture_output=True, text=True, timeout=45,
                env=HELPER_ENV)
            if result.returncode:
                raise RuntimeError('Quota request failed')
            data = json.loads(result.stdout)
            for window in data.get('windows', []):
                window['label'] = {'Current session': 'Session', 'Current week': 'Weekly'}.get(window['label'], window['label'])
            if data.get('unavailable_reason'):
                raise RuntimeError(data['unavailable_reason'])
            windows = {w['label']: w for w in data['windows']}
            if not all(k in windows for k in ('Session', 'Weekly')):
                raise RuntimeError('Quota windows unavailable')
            for w in windows.values():
                if not 0 <= float(w['used_percent']) <= 100:
                    raise ValueError('Invalid quota percentage')
            data['reset_allowed'] = account_id == 'default'
            GLib.idle_add(self.apply, data, generation)
        except Exception as error:
            GLib.idle_add(self.failed, type(error).__name__, generation)

    def publish_label(self, label):
        guide = NAME + ' 100% | W 100%'
        self.indicator.set_label(label, guide)
        # Ayatana suppresses identical labels. Reannounce so a late-attaching
        # GNOME proxy recovers even when usage has not changed since startup.
        self.bus.emit_signal(None, self.menu_path.rsplit('/', 1)[0],
                             'org.kde.StatusNotifierItem', 'XAyatanaNewLabel',
                             GLib.Variant('(ss)', (label, guide)))

    def apply(self, data, generation=None):
        if generation is not None and generation != self.request_generation:
            return False
        self.busy = False
        self.latest_data = data
        if self.details:
            self.details.update(data)
        windows = {w['label']: w for w in data['windows']}
        session = windows['Session']['used_percent']
        week = windows['Weekly']['used_percent']
        self.publish_label(f'{NAME} {session:g}% | W {week:g}%')
        (HOME / ('claude_panel_state.json' if PROVIDER == 'anthropic' else 'panel_state.json')).write_text(json.dumps(data, indent=2))
        print(f'Updated: {NAME} {session:g}% | W {week:g}%', flush=True)
        return False

    def failed(self, error, generation=None):
        if generation is not None and generation != self.request_generation:
            return False
        self.busy = False
        self.latest_data = None
        if self.details:
            self.details.unavailable()
        self.publish_label(NAME + ' unavailable')
        print('Quota refresh failed: ' + error, flush=True)
        return False

panel = CodexPanel()
if '--details' in sys.argv:
    GLib.idle_add(panel.show_details)
Gtk.main()
