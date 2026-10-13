"""Anthropic reports utilization in percent: 1.0 means 1%, never 100%."""
import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def fake_usage_windows(source, mapping, used_key, reset_key, *, fraction=False, model_scoped=frozenset()):
    values = []
    for key, label in mapping:
        used = float(source[key][used_key])
        values.append((label, used * 100 if fraction and used <= 1 else used))
    return values


class PercentFixTests(unittest.TestCase):
    def test_low_utilization_is_not_scaled_to_full(self):
        import anthropic_percent
        module = SimpleNamespace(_usage_windows=fake_usage_windows)
        anthropic_percent.install(module)
        windows = module._usage_windows({'five_hour': {'utilization': 0.0}, 'seven_day': {'utilization': 1.0}},
                                        (('five_hour', 'Current session'), ('seven_day', 'Current week')),
                                        'utilization', 'resets_at', fraction=True)
        self.assertEqual(windows, [('Current session', 0.0), ('Current week', 1.0)])

    def test_install_is_idempotent(self):
        import anthropic_percent
        module = SimpleNamespace(_usage_windows=fake_usage_windows)
        anthropic_percent.install(module)
        once = module._usage_windows
        anthropic_percent.install(module)
        self.assertIs(module._usage_windows, once)


class RealHermesTests(unittest.TestCase):
    """Runs against the installed Hermes code with a fake HTTP payload — no network."""

    def test_real_fetcher_reports_one_percent_as_one_percent(self):
        from runtime_paths import HERMES_PYTHON, HELPER_ENV
        code = (
            'import json, anthropic_percent\n'
            'import agent.account_usage as u\n'
            'anthropic_percent.install(u)\n'
            "u._get_json = lambda *a, **k: {'five_hour': {'utilization': 0.5, 'resets_at': None},"
            " 'seven_day': {'utilization': 1.0, 'resets_at': None}}\n"
            "s = u._fetch_anthropic_account_usage(api_key='sk-ant-oat01-' + 'x' * 40)\n"
            'print(json.dumps([w.used_percent for w in s.windows]))\n'
        )
        try:
            result = subprocess.run([str(HERMES_PYTHON), '-c', code], cwd=ROOT, env=HELPER_ENV,
                                    capture_output=True, text=True, timeout=60)
        except OSError:
            self.skipTest('Hermes interpreter not installed')
        if "No module named 'agent'" in result.stderr:
            self.skipTest('Hermes not installed')
        self.assertEqual(result.returncode, 0, result.stderr[-500:])
        self.assertEqual(json.loads(result.stdout.strip().splitlines()[-1]), [0.5, 1.0])


if __name__ == '__main__':
    unittest.main()
