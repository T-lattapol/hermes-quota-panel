"""GTK colored quota details and explicit reset confirmation."""
import gi
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from quota_ui import usage_color, reset_credits, reset_expiry_lines
import panel_geometry
from runtime_paths import APP_DIR, DISPLAY_ZONE, TIMEZONE_LABEL

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

class UsageDetails:
    def __init__(self, name, provider, refresh, reset, layout_path=None, on_account_changed=None):
        self.name = name
        self.provider = provider
        self.refresh = refresh
        self.reset = reset
        self.data = None
        self.layout_path = Path(layout_path) if layout_path is not None else None
        self.positioned = False
        self.layout_save_source = 0
        self.compact = False
        self.on_account_changed = on_account_changed
        self._setting_accounts = False
        self.window = Gtk.Window(title=name + ' Usage')
        self.window.set_default_size(420, 500)
        self.window.set_size_request(320, 220)
        self.window.set_resizable(True)
        self.window.set_keep_above(True)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.window.connect('delete-event', lambda *_: self.hide())
        self.window.connect('configure-event', self.on_configure)
        self.window.connect('destroy', self.cancel_layout_save)
        header = Gtk.HeaderBar(title=name + ' Usage', show_close_button=True)
        header.set_decoration_layout(':close')
        self.mode_toggle = Gtk.Button(label='Compact')
        self.mode_toggle.set_tooltip_text('Toggle compact mode')
        self.mode_toggle.connect('clicked', lambda *_: self.set_compact(not self.compact))
        header.pack_end(self.mode_toggle)
        hide_button = Gtk.Button.new_from_icon_name('window-minimize-symbolic', Gtk.IconSize.BUTTON)
        hide_button.set_tooltip_text('Hide panel')
        hide_button.connect('clicked', lambda *_: self.hide())
        header.pack_end(hide_button)
        self.window.set_titlebar(header)
        self.window.get_style_context().add_class('quota-details')
        css = Gtk.CssProvider()
        css.load_from_data(b'''
        .quota-details {background: #172128; color: #edf2f5;}
        .quota-details headerbar {background-image: none; background: #172128; color: #edf2f5;}
        .quota-details label {color: #edf2f5;}
        .quota-details .muted {color: #a5b3bc; font-size: 11px;}
        .quota-details .title {font-weight: bold; font-size: 20px;}
        .quota-details .quota-caption {font-weight: bold;}
        .quota-details progressbar trough {background: #34414a; min-height: 12px; border: none; border-radius: 6px;}
        .quota-details progressbar progress {min-height: 12px; border: none; border-radius: 6px;}
        .quota-details progressbar.green progress {background: #52cba2;}
        .quota-details progressbar.amber progress {background: #f5b752;}
        .quota-details progressbar.red progress {background: #f17676;}
        .quota-details button {background-image: none; background: #283740; color: #edf2f5; border: 1px solid #43545f; transition: background-color 120ms ease, border-color 120ms ease, box-shadow 120ms ease;}
        .quota-details button:hover {background: #344954; border-color: #6b9aab;}
        .quota-details button:active {background: #17665c; border-color: #52cba2; box-shadow: inset 0 2px 5px rgba(0, 0, 0, 0.35);}
        .quota-details button:disabled {background: #283740; color: #87949c; border-color: #43545f; box-shadow: none;}
        ''')
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.root = root
        root.set_border_width(20)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(root)
        self.window.add(scroll)
        header = Gtk.Box(spacing=12)
        icon = Gtk.Image.new_from_file(str((APP_DIR / 'icons') / ('claude.svg' if provider == 'anthropic' else 'openai.svg')))
        # SVG files need explicit sizing rather than their default intrinsic size.
        from gi.repository import GdkPixbuf
        icon.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(str((APP_DIR / 'icons') / ('claude.svg' if provider == 'anthropic' else 'openai.svg')), 32, 32, True))
        header.pack_start(icon, False, False, 0)
        self.title = self.label(name + ' Usage', 'title')
        header.pack_start(self.title, True, True, 0)
        root.pack_start(header, False, False, 0)
        self.account_selector = Gtk.ComboBoxText()
        self.account_selector.set_tooltip_text('Choose which stored account to display (does not change sign-in)')
        self.account_selector.connect('changed', self._on_account_selector_changed)
        root.pack_start(self.account_selector, False, False, 0)
        self.account = self.label('Fetching account data…', 'muted')
        root.pack_start(self.account, False, False, 0)
        self.rows = {}
        for key, caption in [('Session', '5-hour window'), ('Weekly', 'Weekly window')]:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
            row = Gtk.Box()
            row.pack_start(self.label(caption, 'quota-caption'), True, True, 0)
            value = self.label('—')
            row.pack_end(value, False, False, 0)
            box.pack_start(row, False, False, 0)
            bar = Gtk.ProgressBar()
            bar.set_fraction(0)
            box.pack_start(bar, False, False, 0)
            detail = self.label('No fresh data', 'muted')
            box.pack_start(detail, False, False, 0)
            self.rows[key] = (value, bar, detail)
            root.pack_start(box, False, False, 0)
        self.status = self.label('Refreshing…', 'muted')
        root.pack_start(self.status, False, False, 0)
        self.expiry_label = self.label('Fetching reset credit expiry…', 'muted')
        self.expiry_label.set_no_show_all(True)
        root.pack_start(self.expiry_label, False, False, 0)
        buttons = Gtk.Box(spacing=10)
        self.refreshing = False
        self.refresh_feedback_source = 0
        self.window.connect('destroy', self.cancel_refresh_feedback)
        self.refresh_button = Gtk.Button(label='Refresh')
        self.refresh_button.connect('clicked', self.request_refresh)
        buttons.pack_start(self.refresh_button, True, True, 0)
        self.reset_button = Gtk.Button(label='Reset usage')
        self.reset_button.connect('clicked', lambda _: self.confirm_reset())
        buttons.pack_start(self.reset_button, True, True, 0)
        self.reset_button.set_no_show_all(True)
        root.pack_start(buttons, False, False, 0)
        self.reset_note = self.label('Resets use one banked credit and require confirmation.', 'muted')
        root.pack_start(self.reset_note, False, False, 0)
        self.reset_note.set_no_show_all(True)
        self.set_compact(panel_geometry.load_compact(self.layout_path) if self.layout_path is not None else False)

    def _mode(self):
        return 'compact' if self.compact else 'full'

    def set_accounts(self, accounts, selected_id=None):
        """Populate the selector with id/label pairs only — never a token."""
        self._setting_accounts = True
        try:
            self.account_selector.remove_all()
            for account in accounts:
                self.account_selector.append(account['id'], account['label'])
            target = selected_id if selected_id is not None else (accounts[0]['id'] if accounts else None)
            if target is not None:
                self.account_selector.set_active_id(target)
        finally:
            self._setting_accounts = False

    def _on_account_selector_changed(self, combo):
        if self._setting_accounts:
            return
        account_id = combo.get_active_id()
        if account_id is None:
            return
        self.clear_for_account_switch()
        if self.on_account_changed:
            self.on_account_changed(account_id)

    def clear_for_account_switch(self):
        """Drop any stale quota immediately so a slow in-flight fetch for the
        PREVIOUS account can never render over the newly-chosen one."""
        self.data = None
        for value, bar, detail in self.rows.values():
            value.set_text('Unavailable')
            bar.set_fraction(0)
            detail.set_text('No fresh data')
        self.status.set_text('Switching account…')
        self.reset_button.set_sensitive(False)

    def apply_mode_visibility(self):
        verbose = (self.account, self.status) + tuple(label for _, _, label in self.rows.values())
        for widget in verbose:
            widget.set_no_show_all(True)
            widget.set_visible(not self.compact)
        for widget in (self.expiry_label, self.reset_button, self.reset_note):
            widget.set_no_show_all(True)
            widget.hide()
        if not self.compact and self.data is not None:
            codex = self.provider == 'openai-codex'
            self.expiry_label.set_visible(codex)
            self.reset_button.set_visible(codex)
            self.reset_note.show()

    def set_compact(self, value):
        value = bool(value)
        if value != self.compact and self.window.get_mapped():
            self.cancel_layout_save()
            self.save_layout()  # Save outgoing mode BEFORE changing the key.
        self.compact = value
        self.mode_toggle.set_label('Full' if value else 'Compact')
        self.mode_toggle.set_tooltip_text('Switch to full mode' if value else 'Switch to compact mode')
        self.root.set_spacing(8 if value else 14)
        self.root.set_border_width(12 if value else 20)
        self.apply_mode_visibility()
        if self.layout_path is not None:
            panel_geometry.save_compact(self.layout_path, value)
        if not self.restore_layout():
            self.window.resize(360 if value else 420, 330 if value else 500)

    def request_refresh(self, *_):
        if self.refreshing:
            return
        self.cancel_refresh_feedback()
        self.refreshing = True
        self.refresh_button.set_label('Refreshing…')
        self.refresh_button.set_sensitive(False)
        self.status.set_text('Refreshing…')
        self.refresh()

    def finish_refresh(self, success):
        if self.refreshing:
            self.refreshing = False
            self.refresh_button.set_label('Refresh ✓' if success else 'Retry refresh')
            self.refresh_button.set_sensitive(True)
            if success:
                self.refresh_feedback_source = GLib.timeout_add(1500, self.clear_refresh_feedback)

    def cancel_refresh_feedback(self, *_):
        if self.refresh_feedback_source:
            GLib.source_remove(self.refresh_feedback_source)
            self.refresh_feedback_source = 0

    def clear_refresh_feedback(self):
        self.refresh_feedback_source = 0
        if not self.refreshing:
            self.refresh_button.set_label('Refresh')
        return False

    def label(self, text, style=None):
        label = Gtk.Label(label=text)
        label.set_xalign(0)
        label.set_line_wrap(True)
        if style:
            label.get_style_context().add_class(style)
        return label

    def show(self):
        # Re-read the shared geometry every time, not just on first show: the OTHER
        # provider's process may have moved/resized the common panel while this
        # window was hidden, and the handoff must honor that latest geometry.
        restored = self.restore_layout()
        if restored:
            self.positioned = True
        self.window.show_all()
        if self.data:
            self.update(self.data, refresh_complete=False)
        else:
            self.reset_button.hide()
            self.reset_note.hide()
        if not restored and not self.positioned:
            monitor = Gdk.Display.get_default().get_primary_monitor()
            if monitor:
                rect = monitor.get_workarea()
                width, _ = self.window.get_size()
                self.window.move(rect.x + rect.width - width - 24, rect.y + 16)
            self.positioned = True
        self.apply_mode_visibility()
        self.window.present()
        native = self.window.get_window()
        if native:
            native.raise_()
        if self.data is None:
            self.refresh()

    def restore_layout(self):
        if self.layout_path is None:
            return False
        layout = panel_geometry.load_geometry(self.layout_path, self._mode())
        if layout is None:
            return False
        x, y, width, height = (layout[key] for key in ('x', 'y', 'width', 'height'))
        display = Gdk.Display.get_default()
        monitor = display.get_monitor_at_point(x, y)
        if monitor:
            rect = monitor.get_workarea()
            width = min(max(320, width), rect.width)
            height = min(max(220, height), rect.height)
            x = max(rect.x, min(x, rect.x + rect.width - width))
            y = max(rect.y, min(y, rect.y + rect.height - height))
        self.window.resize(width, height)
        self.window.move(x, y)
        return True

    def on_configure(self, *_):
        if self.layout_path is not None:
            self.cancel_layout_save()
            self.layout_save_source = GLib.timeout_add(350, self.save_layout)
        return False

    def cancel_layout_save(self, *_):
        if self.layout_save_source:
            GLib.source_remove(self.layout_save_source)
            self.layout_save_source = 0

    def save_layout(self):
        self.layout_save_source = 0
        if self.layout_path is not None and self.window.get_mapped():
            x, y = self.window.get_position()
            width, height = self.window.get_size()
            try:
                panel_geometry.save_geometry(self.layout_path, self._mode(), dict(x=x, y=y, width=width, height=height))
            except OSError as error:
                print(f'Panel layout could not be saved: {type(error).__name__}', flush=True)
        return False

    def hide(self):
        # Save synchronously BEFORE hiding: if the other provider is about to show
        # itself (DBus Shown handoff), its restore_layout() read must see this
        # window's latest position/size, not a stale debounced value.
        self.cancel_layout_save()
        self.save_layout()
        self.window.hide()
        return True

    def update(self, data, refresh_complete=True):
        self.data = data
        zone = DISPLAY_ZONE
        self.title.set_text(self.name + (' · ' + str(data['plan']) if data.get('plan') else ' Usage'))
        self.account.set_text('Account: ' + data.get('account_label', 'OpenAI Codex OAuth'))
        windows = {w['label']: w for w in data.get('windows', [])}
        for key, (value_label, bar, detail) in self.rows.items():
            w = windows.get(key)
            if not w:
                value_label.set_text('Unavailable')
                continue
            used = float(w['used_percent'])
            value_label.set_text(f'{used:g}% used')
            bar.set_fraction(used / 100)
            context = bar.get_style_context()
            for color in ('green', 'amber', 'red'):
                context.remove_class(color)
            context.add_class(usage_color(used))
            reset = datetime.fromisoformat(w['resets_at']).astimezone(zone).strftime('%d %b %H:%M') if w.get('resets_at') else 'unknown'
            detail.set_text(f'{100-used:g}% remaining · resets {reset} {TIMEZONE_LABEL}')
        stamp = datetime.fromisoformat(data['fetched_at']).astimezone(zone).strftime('%H:%M:%S')
        self.status.set_text(f'Updated {stamp} {TIMEZONE_LABEL} · refresh every 60s')
        credits = reset_credits(data)
        self.expiry_label.set_text('\n'.join(reset_expiry_lines(data)))
        self.expiry_label.set_visible(self.provider == 'openai-codex')
        if self.provider == 'openai-codex':
            self.reset_button.show()
            self.reset_note.show()
            allowed = data.get('reset_allowed', True) is True
            self.reset_button.set_label(f'Reset usage ({credits} credits)')
            self.reset_button.set_sensitive(allowed and credits > 0)
            self.reset_note.set_text('Resets use one banked credit and require confirmation.' if allowed else 'Reset is available only for the default account.')
        else:
            self.reset_button.hide()
            self.reset_note.show()
            self.reset_note.set_text('Manual reset is not available for this account.')
        if refresh_complete:
            self.finish_refresh(True)
        if self.refreshing:
            self.status.set_text('Refreshing…')
        self.apply_mode_visibility()

    def unavailable(self):
        self.finish_refresh(False)
        self.data = None
        self.reset_button.set_sensitive(False)
        self.status.set_text('Refresh failed · retrying in 60s')
        for value, bar, detail in self.rows.values():
            value.set_text('Unavailable')
            bar.set_fraction(0)
            detail.set_text('No fresh data')
        self.apply_mode_visibility()

    def confirm_reset(self):
        if not self.data or self.data.get('reset_allowed', True) is not True or not reset_credits(self.data):
            return
        dialog = Gtk.MessageDialog(transient_for=self.window, modal=True, message_type=Gtk.MessageType.WARNING,
                                   buttons=Gtk.ButtonsType.NONE, text='Use one banked Codex reset?')
        dialog.format_secondary_text('This spends one reset credit and restores your 5-hour and weekly allowance.\nIt is not a free refresh. You cannot undo it.')
        dialog.add_button('Cancel', Gtk.ResponseType.CANCEL)
        confirm = dialog.add_button('Use 1 reset credit', Gtk.ResponseType.OK)
        force = Gtk.CheckButton(label='Allow early reset even before the quota is exhausted')
        force.set_active(False)
        dialog.get_content_area().pack_start(force, False, False, 8)
        exhausted = any(float(w['used_percent']) >= 100 for w in self.data.get('windows', []) if w['label'] in ('Session', 'Weekly'))
        confirm.set_sensitive(exhausted)
        force.connect('toggled', lambda button: confirm.set_sensitive(exhausted or button.get_active()))
        dialog.show_all()
        response = dialog.run()
        forced = force.get_active()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            self.reset_button.set_sensitive(False)
            self.status.set_text('Requesting reset…')
            self.reset(forced)
