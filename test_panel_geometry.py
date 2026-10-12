"""TDD for shared cross-provider panel geometry storage."""
import json
import tempfile
import time
import unittest
from pathlib import Path

import panel_geometry as pg


class SharedGeometryTests(unittest.TestCase):
    def test_save_then_load_round_trips_for_a_mode(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'shared.json'
            pg.save_geometry(path, 'full', dict(x=10, y=20, width=400, height=300))
            self.assertEqual(pg.load_geometry(path, 'full'), dict(x=10, y=20, width=400, height=300))

    def test_saving_one_mode_does_not_clobber_the_other_mode(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'shared.json'
            pg.save_geometry(path, 'full', dict(x=1, y=2, width=400, height=300))
            pg.save_geometry(path, 'compact', dict(x=3, y=4, width=200, height=120))
            self.assertEqual(pg.load_geometry(path, 'full'), dict(x=1, y=2, width=400, height=300))
            self.assertEqual(pg.load_geometry(path, 'compact'), dict(x=3, y=4, width=200, height=120))

    def test_saving_from_two_providers_in_sequence_is_the_last_writer_wins_without_overwriting_other_mode(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'shared.json'
            # Provider A (Claude) saves full geometry.
            pg.save_geometry(path, 'full', dict(x=10, y=10, width=420, height=350))
            # Provider B (Codex) then moves and saves the SAME shared full geometry.
            pg.save_geometry(path, 'full', dict(x=50, y=60, width=450, height=380))
            self.assertEqual(pg.load_geometry(path, 'full'), dict(x=50, y=60, width=450, height=380))

    def test_load_missing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(pg.load_geometry(Path(folder) / 'missing.json', 'full'))

    def test_load_invalid_geometry_returns_none(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'shared.json'
            path.write_text(json.dumps({'full': {'x': 1, 'y': 2, 'width': -5, 'height': 300}}))
            self.assertIsNone(pg.load_geometry(path, 'full'))

    def test_migrate_legacy_flat_file_becomes_full_mode_in_shared_file(self):
        with tempfile.TemporaryDirectory() as folder:
            shared = Path(folder) / 'shared.json'
            legacy = Path(folder) / 'panel_layout.json'
            legacy.write_text(json.dumps(dict(x=2095, y=1493, width=441, height=385)))
            pg.migrate_legacy(shared, [legacy])
            self.assertEqual(pg.load_geometry(shared, 'full'), dict(x=2095, y=1493, width=441, height=385))

    def test_migrate_legacy_picks_the_most_recently_modified_source(self):
        with tempfile.TemporaryDirectory() as folder:
            shared = Path(folder) / 'shared.json'
            older = Path(folder) / 'panel_layout.json'
            newer = Path(folder) / 'claude_panel_layout.json'
            older.write_text(json.dumps(dict(x=1, y=1, width=400, height=300)))
            time.sleep(0.01)
            newer.write_text(json.dumps(dict(x=9, y=9, width=420, height=350)))
            pg.migrate_legacy(shared, [older, newer])
            self.assertEqual(pg.load_geometry(shared, 'full'), dict(x=9, y=9, width=420, height=350))

    def test_migrate_legacy_never_overwrites_an_existing_shared_file(self):
        with tempfile.TemporaryDirectory() as folder:
            shared = Path(folder) / 'shared.json'
            pg.save_geometry(shared, 'full', dict(x=77, y=88, width=500, height=400))
            legacy = Path(folder) / 'panel_layout.json'
            legacy.write_text(json.dumps(dict(x=1, y=1, width=100, height=100)))
            pg.migrate_legacy(shared, [legacy])
            self.assertEqual(pg.load_geometry(shared, 'full'), dict(x=77, y=88, width=500, height=400))

    def test_migrate_legacy_with_no_sources_and_no_shared_file_is_a_safe_noop(self):
        with tempfile.TemporaryDirectory() as folder:
            shared = Path(folder) / 'shared.json'
            pg.migrate_legacy(shared, [Path(folder) / 'absent.json'])
            self.assertFalse(shared.exists())

    def test_compact_flag_round_trips_and_defaults_to_false(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'shared.json'
            self.assertFalse(pg.load_compact(path))
            pg.save_compact(path, True)
            self.assertTrue(pg.load_compact(path))
            pg.save_compact(path, False)
            self.assertFalse(pg.load_compact(path))

    def test_compact_flag_and_geometry_coexist_without_clobbering_each_other(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'shared.json'
            pg.save_geometry(path, 'full', dict(x=1, y=2, width=400, height=300))
            pg.save_compact(path, True)
            pg.save_geometry(path, 'compact', dict(x=5, y=6, width=200, height=150))
            self.assertEqual(pg.load_geometry(path, 'full'), dict(x=1, y=2, width=400, height=300))
            self.assertTrue(pg.load_compact(path))
            self.assertEqual(pg.load_geometry(path, 'compact'), dict(x=5, y=6, width=200, height=150))


if __name__ == '__main__':
    unittest.main()
