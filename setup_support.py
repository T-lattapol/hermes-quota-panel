"""Setup-only discovery and non-secret settings persistence."""
import json
import os
import tempfile
import subprocess
import shutil
import shlex
from pathlib import Path
from configuration import ALLOWED_SETTINGS, config_path, read_settings, safe_value


def write_config(settings, config_home=None):
    if not isinstance(settings, dict) or any(key not in ALLOWED_SETTINGS or not safe_value(value) for key, value in settings.items()):
        raise ValueError('Only non-secret path/timezone settings are permitted; no configuration written')
    env = dict(os.environ)
    if config_home is not None:
        env['XDG_CONFIG_HOME'] = str(config_home)
    destination = config_path(env)
    document = read_settings(env)
    document.update(settings)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix='.config-', suffix='.tmp', dir=destination.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(document, stream, indent=2)
            stream.write('\n')
        os.chmod(temporary, 0o600)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return destination


_PROBE = """import inspect,json,sys
from pathlib import Path
import agent.account_usage as usage
from agent.credential_pool import PooledCredential
from hermes_cli.subcommands.usage import usage_snapshot_document
assert 'read_only' in inspect.signature(usage.fetch_account_usage).parameters
assert hasattr(usage, 'redeem_codex_reset_credit')
assert hasattr(usage, '_fetch_anthropic_account_usage')
assert hasattr(usage, '_resolve_codex_usage_credentials')
assert callable(PooledCredential.from_dict)
assert callable(usage_snapshot_document)
print(json.dumps({'root':str(Path(usage.__file__).resolve().parent.parent),'python':sys.executable}))
"""


def discover_hermes(env=None):
    env = dict(os.environ if env is None else env)
    settings = read_settings(env)
    home = Path(env.get('HOME') or str(Path.home()))
    auth_home = Path(settings.get('HERMES_HOME') or str(home / '.hermes')).expanduser().absolute()
    root = Path(settings.get('HERMES_AGENT_DIR') or str(auth_home / 'hermes-agent')).expanduser().absolute()
    candidates = [(settings.get('HERMES_PYTHON') or str(root / 'venv' / 'bin' / 'python'), root)]
    cli = shutil.which('hermes', path=env.get('PATH') or os.defpath)
    if cli:
        script = Path(cli).resolve()
        sibling = script.parent / 'python'
        if sibling.is_file():
            candidates.append((str(sibling), sibling.parent.parent.parent))
        try:
            with script.open('rb') as stream:
                first = stream.readline(1024).decode('utf-8', errors='replace').strip()
            if first.startswith('#!'):
                raw = first[2:].strip()
                if Path(raw).is_file():
                    interpreter = raw  # Preserve a venv path, even if it contains spaces.
                else:
                    words = shlex.split(raw)
                    if words and Path(words[0]).name == 'env':
                        names = [word for word in words[1:] if not word.startswith('-')]
                        interpreter = shutil.which(names[0], path=env.get('PATH') or os.defpath) if names else None
                    else:
                        interpreter = words[0] if words else None
                if interpreter:
                    binary = Path(interpreter).expanduser().absolute()
                    candidates.append((str(binary), binary.parent.parent.parent))
        except (OSError, ValueError):
            pass
    if env.get('HERMES_PYTHON') or env.get('HERMES_AGENT_DIR'):
        candidates = candidates[:1]  # Respect explicit choices; only stale saved settings may fall back.
    seen = set()
    for python, source in candidates:
        if python in seen:
            continue
        seen.add(python)
        probe_env = {**env, 'HERMES_HOME': str(auth_home),
                     'PYTHONPATH': os.pathsep.join(filter(None, [str(source), env.get('PYTHONPATH', '')]))}
        try:
            result = subprocess.run([python, '-c', _PROBE], env=probe_env, text=True, capture_output=True, timeout=15)
            metadata = json.loads(result.stdout) if result.returncode == 0 else {}
        except (OSError, ValueError, subprocess.TimeoutExpired):
            metadata = {}
        if isinstance(metadata, dict) and safe_value(metadata.get('root')) and safe_value(metadata.get('python')):
            return {'HERMES_HOME': str(auth_home), 'HERMES_AGENT_DIR': metadata['root'], 'HERMES_PYTHON': metadata['python']}
    raise RuntimeError('No compatible Hermes installation found; check HERMES_AGENT_DIR and HERMES_PYTHON')
