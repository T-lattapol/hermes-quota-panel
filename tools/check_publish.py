"""Audit tracked files without printing offending secret values."""
import argparse
import fnmatch
import json
import re
import subprocess
from pathlib import Path

BANNED_NAMES = ('auth.json', 'account_preferences.json', '*panel_state.json', '*panel_layout.json',
                '*.lock', '*.log', '.env', '.env.*', 'credentials*', '.install-manifest.json', '*.deb', '*.so*')
BANNED_DIRS = {'deps', 'verification', 'gnome_sources', 'venv', '.venv', '__pycache__'}
PATTERNS = {
    'credential-like token': re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{24,}|sk-(?:ant-[A-Za-z0-9_-]{24,}|[A-Za-z0-9_-]{32,})|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,})'),
    'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'machine-specific home path': re.compile(r'/home/[A-Za-z0-9_.-]+'),
}


def audit_files(root, files):
    root = Path(root).resolve()
    issues = []
    for name in files:
        relative = Path(name)
        path = root / relative
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            issues.append(f'{name}: symlink or outside repository')
            continue
        if any(part in BANNED_DIRS for part in relative.parts) or any(fnmatch.fnmatch(relative.name, pattern) for pattern in BANNED_NAMES):
            issues.append(f'{name}: personal/runtime artifact is not publishable')
            continue
        try:
            content = path.read_text()
        except UnicodeDecodeError:
            continue  # Images are reviewed separately; no generated quota screenshots are copied.
        if path.suffix == '.json' and relative.parts[:2] == ('tests', 'fixtures'):
            try:
                fixture = json.loads(content)
                if not isinstance(fixture, dict) or fixture.get('fixture') is not True:
                    issues.append(f'{name}: JSON fixture must be explicitly synthetic')
            except ValueError:
                issues.append(f'{name}: invalid fixture JSON')
        for label, pattern in PATTERNS.items():
            if pattern.search(content):
                issues.append(f'{name}: possible {label}')
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = subprocess.run(['git', 'ls-files', '-z'], cwd=args.root, capture_output=True, check=True)
    files = [value.decode() for value in result.stdout.split(b'\0') if value]
    if not files:
        raise SystemExit('No tracked files: stage the reviewed source allowlist first.')
    issues = audit_files(args.root, files)
    for issue in issues:
        print(issue)
    print(f'Publish audit: {len(files)} tracked files, {len(issues)} issues')
    raise SystemExit(1 if issues else 0)


if __name__ == '__main__':
    main()
