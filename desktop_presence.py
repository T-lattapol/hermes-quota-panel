"""Detect the packaged Hermes Desktop main process without reading credentials."""
import os
from pathlib import Path


def desktop_running(proc_root=Path('/proc')):
    try:
        entries = Path(proc_root).iterdir()
        for entry in entries:
            if not entry.name.isdigit():
                continue
            try:
                if entry.stat().st_uid != os.getuid():
                    continue
                argv = entry.joinpath('cmdline').read_bytes().split(b'\0')
                if not argv or not argv[0]:
                    continue
                name = Path(os.fsdecode(argv[0])).name
                if name.lower() == 'hermes' and not any(arg.startswith(b'--type=') for arg in argv):
                    # CLI is a Python script, not the packaged Hermes executable.
                    return True
            except (OSError, ValueError):
                continue  # Process disappeared, or belongs to another user.
    except OSError:
        pass
    return False


def should_show(mode, running):
    return mode == 'always' or running
