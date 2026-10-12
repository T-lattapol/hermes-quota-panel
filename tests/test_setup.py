"""Tests for the convenience setup coordinator (setup.py). All system side
effects (sudo/apt-get, Hermes discovery, config writes, install, process
start, extension enable) are injected as fakes; nothing here touches the
real machine. See setup.py module docstring for the dependency contract.
"""
import io
import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

import setup


class FakeConflicts:
    def __init__(self, running=False, old_autostart=None):
        self.running = running
        self.old_autostart = old_autostart or []

    def __call__(self, **kwargs):
        return {'running': self.running, 'old_autostart': self.old_autostart}


def ok_discover(env=None):
    return {'HERMES_HOME': '/example/user/.hermes', 'HERMES_AGENT_DIR': '/example/user/.hermes/hermes-agent',
            'HERMES_PYTHON': '/example/user/.hermes/hermes-agent/venv/bin/python'}


def noop_write_config(*a, **k):
    pass


def noop_install(*a, **k):
    pass


def noop_start(*a, **k):
    pass


class SetupDryRunTests(unittest.TestCase):
    def test_dry_run_reports_plan_and_touches_nothing(self):
        calls = []
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = setup.main(
                ['--dry-run'],
                env={},
                discover_hermes=ok_discover,
                write_config=lambda *a, **k: calls.append(('write_config', a, k)),
                install_fn=lambda *a, **k: calls.append(('install', a, k)),
                find_conflicts=FakeConflicts(),
                start_viewer=lambda *a, **k: calls.append(('start', a, k)),
                detect_missing_packages=lambda **k: [],
            )
        self.assertEqual(code, 0)
        self.assertEqual(calls, [])
        self.assertIn('dry_run', buf.getvalue())

    def test_stops_with_nonzero_when_hermes_unavailable(self):
        calls = []

        def boom(env=None):
            raise RuntimeError('Hermes not found at any known location')

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = setup.main(
                ['--dry-run'],
                env={},
                discover_hermes=boom,
                write_config=lambda *a, **k: calls.append('write_config'),
                install_fn=lambda *a, **k: calls.append('install'),
                find_conflicts=FakeConflicts(),
                start_viewer=lambda *a, **k: calls.append('start'),
                detect_missing_packages=lambda **k: [],
            )
        self.assertNotEqual(code, 0)
        self.assertEqual(calls, [])
        self.assertIn('Hermes not found', buf.getvalue())


class PackageConfirmationTests(unittest.TestCase):
    def test_noninteractive_never_runs_apt_get_even_with_missing_packages(self):
        apt_calls = []
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = setup.main(
                [],
                env={},
                discover_hermes=ok_discover,
                write_config=noop_write_config,
                install_fn=noop_install,
                find_conflicts=FakeConflicts(),
                start_viewer=noop_start,
                detect_missing_packages=lambda **k: ['python3-gi'],
                apt_install=lambda packages: apt_calls.append(packages),
                isatty=lambda: False,
            )
        self.assertEqual(apt_calls, [])
        self.assertIn('python3-gi', buf.getvalue())
        self.assertIn('apt-get', buf.getvalue())

    def test_no_packages_flag_skips_confirmation_and_apt_get(self):
        apt_calls = []
        input_calls = []
        code = setup.main(
            ['--no-packages'],
            env={},
            discover_hermes=ok_discover,
            write_config=noop_write_config,
            install_fn=noop_install,
            find_conflicts=FakeConflicts(),
            start_viewer=noop_start,
            detect_missing_packages=lambda **k: ['python3-gi'],
            apt_install=lambda packages: apt_calls.append(packages),
            input_fn=lambda prompt: input_calls.append(prompt) or 'y',
            isatty=lambda: True,
        )
        self.assertEqual(apt_calls, [])
        self.assertEqual(input_calls, [])

    def test_interactive_confirmation_yes_runs_apt_get_with_missing_packages(self):
        apt_calls = []
        code = setup.main(
            [],
            env={},
            discover_hermes=ok_discover,
            write_config=noop_write_config,
            install_fn=noop_install,
            find_conflicts=FakeConflicts(),
            start_viewer=noop_start,
            detect_missing_packages=lambda **k: ['python3-gi', 'gir1.2-gtk-3.0'],
            apt_install=lambda packages: apt_calls.append(list(packages)),
            input_fn=lambda prompt: 'y',
            isatty=lambda: True,
        )
        self.assertEqual(code, 0)
        self.assertEqual(apt_calls, [['python3-gi', 'gir1.2-gtk-3.0']])

    def test_interactive_confirmation_declined_skips_apt_get(self):
        apt_calls = []
        code = setup.main(
            [],
            env={},
            discover_hermes=ok_discover,
            write_config=noop_write_config,
            install_fn=noop_install,
            find_conflicts=FakeConflicts(),
            start_viewer=noop_start,
            detect_missing_packages=lambda **k: ['python3-gi'],
            apt_install=lambda packages: apt_calls.append(packages),
            input_fn=lambda prompt: 'n',
            isatty=lambda: True,
        )
        self.assertEqual(code, 1, 'Declining required libraries must stop setup, not claim success')
        self.assertEqual(apt_calls, [])

    def test_dry_run_never_runs_apt_get_even_when_interactive(self):
        apt_calls = []
        code = setup.main(
            ['--dry-run'],
            env={},
            discover_hermes=ok_discover,
            write_config=noop_write_config,
            install_fn=noop_install,
            find_conflicts=FakeConflicts(),
            start_viewer=noop_start,
            detect_missing_packages=lambda **k: ['python3-gi'],
            apt_install=lambda packages: apt_calls.append(packages),
            input_fn=lambda prompt: 'y',
            isatty=lambda: True,
        )
        self.assertEqual(apt_calls, [])


class ConflictAndFullRunTests(unittest.TestCase):
    def test_no_conflict_installs_with_autostart_and_starts_both_providers(self):
        calls = []
        code = setup.main(
            [],
            env={},
            discover_hermes=ok_discover,
            write_config=lambda settings, **k: calls.append(('write_config', settings)),
            install_fn=lambda *a, **k: calls.append(('install', a, k)),
            find_conflicts=FakeConflicts(running=False, old_autostart=[]),
            start_viewer=lambda provider, **k: calls.append(('start', provider)),
            detect_missing_packages=lambda **k: [],
        )
        self.assertEqual(code, 0)
        kinds = [c[0] for c in calls]
        self.assertIn('write_config', kinds)
        self.assertIn('install', kinds)
        install_call = next(c for c in calls if c[0] == 'install')
        self.assertTrue(install_call[2].get('autostart'))
        started = sorted(c[1] for c in calls if c[0] == 'start')
        self.assertEqual(started, ['claude', 'codex'])

    def test_running_viewer_skips_autostart_and_start_but_still_installs(self):
        calls = []
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = setup.main(
                [],
                env={},
                discover_hermes=ok_discover,
                write_config=lambda settings, **k: calls.append(('write_config', settings)),
                install_fn=lambda *a, **k: calls.append(('install', a, k)),
                find_conflicts=FakeConflicts(running=True, old_autostart=[]),
                start_viewer=lambda provider, **k: calls.append(('start', provider)),
                detect_missing_packages=lambda **k: [],
            )
        self.assertEqual(code, 0)
        self.assertFalse(any(c[0] == 'start' for c in calls))
        install_call = next(c for c in calls if c[0] == 'install')
        self.assertFalse(install_call[2].get('autostart'))
        self.assertIn('migrat', buf.getvalue().lower())

    def test_old_autostart_files_skip_autostart_and_start(self):
        calls = []
        code = setup.main(
            [],
            env={},
            discover_hermes=ok_discover,
            write_config=lambda settings, **k: calls.append(('write_config', settings)),
            install_fn=lambda *a, **k: calls.append(('install', a, k)),
            find_conflicts=FakeConflicts(running=False, old_autostart=['codex-quota.desktop']),
            start_viewer=lambda provider, **k: calls.append(('start', provider)),
            detect_missing_packages=lambda **k: [],
        )
        self.assertEqual(code, 0)
        self.assertFalse(any(c[0] == 'start' for c in calls))
        install_call = next(c for c in calls if c[0] == 'install')
        self.assertFalse(install_call[2].get('autostart'))

    def test_no_start_flag_skips_launch_but_keeps_autostart(self):
        calls = []
        code = setup.main(
            ['--no-start'],
            env={},
            discover_hermes=ok_discover,
            write_config=lambda settings, **k: calls.append(('write_config', settings)),
            install_fn=lambda *a, **k: calls.append(('install', a, k)),
            find_conflicts=FakeConflicts(running=False, old_autostart=[]),
            start_viewer=lambda provider, **k: calls.append(('start', provider)),
            detect_missing_packages=lambda **k: [],
        )
        self.assertEqual(code, 0)
        self.assertFalse(any(c[0] == 'start' for c in calls))
        install_call = next(c for c in calls if c[0] == 'install')
        self.assertTrue(install_call[2].get('autostart'))

    def test_write_config_receives_discovered_hermes_paths(self):
        captured = {}
        setup.main(
            [],
            env={},
            discover_hermes=ok_discover,
            write_config=lambda settings, **k: captured.update(settings),
            install_fn=noop_install,
            find_conflicts=FakeConflicts(),
            start_viewer=noop_start,
            detect_missing_packages=lambda **k: [],
        )
        self.assertEqual(captured.get('HERMES_AGENT_DIR'), '/example/user/.hermes/hermes-agent')
        self.assertEqual(captured.get('HERMES_PYTHON'), '/example/user/.hermes/hermes-agent/venv/bin/python')


class SetupShWiringTests(unittest.TestCase):
    """Run the real shell/Python wiring with a hermetic external-interpreter fixture."""

    def test_setup_sh_dry_run_prints_plan_and_exits_zero(self):
        repo = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as folder:
            root = Path(folder)
            native = root / 'native-python'
            sdk = root / 'sdk'
            metadata = json.dumps({'root': str(sdk), 'python': str(native)})
            native.write_text('#!/usr/bin/python3\n# Synthetic interpreter response for setup wiring test.\nprint(' + repr(metadata) + ')\n')
            native.chmod(0o755)
            env = {**os.environ, 'HERMES_PYTHON': str(native), 'HERMES_AGENT_DIR': str(sdk),
                   'XDG_CONFIG_HOME': str(root / 'config'), 'XDG_DATA_HOME': str(root / 'data')}
            result = subprocess.run(['bash', str(repo / 'setup.sh'), '--dry-run', '--no-packages', '--no-start', '--no-extension'],
                                    cwd=repo, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('"dry_run": true', result.stdout)
            self.assertIn(str(sdk), result.stdout)
            self.assertFalse((root / 'config').exists())
            self.assertFalse((root / 'data').exists())

    def test_setup_sh_reports_clear_error_when_hermes_unavailable(self):
        repo = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as folder:
            root = Path(folder)
            env = {**os.environ, 'HERMES_PYTHON': str(root / 'missing-python'),
                   'XDG_CONFIG_HOME': str(root / 'config'), 'XDG_DATA_HOME': str(root / 'data')}
            result = subprocess.run(['bash', str(repo / 'setup.sh'), '--dry-run'],
                                    cwd=repo, env=env, capture_output=True, text=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('No compatible Hermes', result.stdout)
            self.assertFalse((root / 'config').exists())
            self.assertFalse((root / 'data').exists())

class SetupSafetyTests(unittest.TestCase):
    def test_missing_packages_do_not_claim_success_or_start_an_unusable_viewer(self):
        calls = []
        with redirect_stdout(io.StringIO()):
            code = setup.main(['--no-packages'], env={}, discover_hermes=ok_discover,
                write_config=lambda *a, **k: calls.append('config'),
                install_fn=lambda *a, **k: calls.append('install'),
                start_viewer=lambda *a, **k: calls.append('start'),
                detect_missing_packages=lambda **k: ['python3-gi'])
        self.assertEqual(code, 1)
        self.assertEqual(calls, [])

    def test_dependency_probe_uses_the_requested_gui_environment(self):
        from unittest.mock import Mock
        runner = Mock(return_value=Mock(returncode=0))
        missing = setup.default_detect_missing_packages(env={'QUOTA_PANEL_GUI_PYTHON': '/custom/gui-python', 'TEST_MARKER': 'passed'}, runner=runner)
        self.assertEqual(missing, [])
        self.assertEqual(runner.call_args.args[0][0], '/custom/gui-python')
        self.assertEqual(runner.call_args.kwargs['env']['TEST_MARKER'], 'passed')
        self.assertIn('GdkPixbuf', runner.call_args.args[0][-1])


if __name__ == '__main__':
    unittest.main()
