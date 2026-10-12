import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {isQuotaIndicatorId} from './click-routing.js';

export default class QuotaDirectClick extends Extension {
    enable() {
        this._captureId = global.stage.connect('captured-event', (_stage, event) => this._capture(event));
    }

    disable() {
        if (this._captureId) {
            global.stage.disconnect(this._captureId);
            this._captureId = 0;
        }
    }

    _capture(event) {
        const type = event.type();
        if (type !== Clutter.EventType.BUTTON_PRESS && type !== Clutter.EventType.BUTTON_RELEASE)
            return Clutter.EVENT_PROPAGATE;
        if (![1, 2, 3].includes(event.get_button()))
            return Clutter.EVENT_PROPAGATE;
        const [x, y] = event.get_coords();
        const actor = global.stage.get_actor_at_pos(Clutter.PickMode.REACTIVE, x, y);
        for (const button of Object.values(Main.panel.statusArea)) {
            const indicator = button?._indicator;
            if (!indicator || !isQuotaIndicatorId(indicator.id))
                continue;
            if (!actor || (actor !== button && !button.contains(actor)))
                continue;
            // Stop the event before AppIndicator opens its native menu.
            // This is scoped to our two indicators; all other panel buttons are untouched.
            if (type === Clutter.EventType.BUTTON_PRESS) {
                button.menu?.close();
                this._open(indicator, event.get_time());
            }
            return Clutter.EVENT_STOP;
        }
        return Clutter.EVENT_PROPAGATE;
    }

    _open(indicator, time) {
        Gio.DBus.session.call(
            indicator.busName, indicator.menuPath,
            'com.canonical.dbusmenu', 'Event',
            new GLib.Variant('(isvu)', [0, 'opened', new GLib.Variant('i', 0), time]),
            null, Gio.DBusCallFlags.NONE, 5000, null,
            (connection, result) => {
                try {
                    connection.call_finish(result);
                } catch (error) {
                    console.error('Quota direct click: unable to open details', error);
                }
            });
    }
}
