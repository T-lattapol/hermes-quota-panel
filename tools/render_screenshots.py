"""Render the real GTK panel using only synthetic fixtures, without network/auth.
Run: xvfb-run -a /usr/bin/python3 tools/render_screenshots.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from usage_details import UsageDetails


def pump():
    GLib.timeout_add(250, Gtk.main_quit)
    Gtk.main()


def main():
    out = ROOT / 'docs' / 'images'
    out.mkdir(parents=True, exist_ok=True)
    for name, provider, fixture in [('Codex', 'openai-codex', 'codex'), ('Claude', 'anthropic', 'claude')]:
        data = json.loads((ROOT / 'tests' / 'fixtures' / (fixture + '_snapshot.json')).read_text())
        assert data.get('fixture') is True
        detail = UsageDetails(name, provider, lambda: None, lambda _: None)
        detail.set_accounts([{'id': 'default', 'label': 'Demo account (sample data)', 'is_default': True}], 'default')
        detail.update(data)
        detail.show()
        detail.window.resize(500, 560)
        detail.window.move(20, 20)
        pump()
        for compact in (False, True):
            detail.set_compact(compact)
            detail.window.resize(500, 300 if compact else 560)
            pump()
            width, height = detail.window.get_size()
            image = Gdk.pixbuf_get_from_window(detail.window.get_window(), 0, 0, width, height)
            assert image is not None
            path = out / (fixture + ('-compact.png' if compact else '-full.png'))
            image.savev(str(path), 'png', [], [])
            print(path.relative_to(ROOT), width, height)
        detail.window.destroy()


if __name__ == '__main__':
    main()
