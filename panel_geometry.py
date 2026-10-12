"""Shared cross-provider panel geometry storage.

Both the Codex and Claude tray processes point at ONE json file so the details
window keeps a common position/size no matter which provider last moved it.
Reads/writes are flock-protected and merge rather than clobber, because the
two provider processes can save at nearly the same moment during a handoff.
"""
import fcntl
import json
from pathlib import Path

_KEYS = ('x', 'y', 'width', 'height')


def _valid(geometry):
    if not isinstance(geometry, dict) or any(type(geometry.get(key)) is not int for key in _KEYS):
        return False
    return geometry['width'] > 0 and geometry['height'] > 0


def _locked_read(path):
    try:
        handle = open(path, 'r')
    except OSError:
        return {}
    with handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_SH)
        except OSError:
            pass
        try:
            document = json.loads(handle.read())
        except ValueError:
            return {}
    return document if isinstance(document, dict) else {}


def _locked_merge_write(path, mutate):
    """Read-modify-write the shared document under an exclusive lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + '.lock')
    with open(lock_path, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            document = {}
            if path.exists():
                try:
                    document = json.loads(path.read_text())
                except ValueError:
                    document = {}
            if not isinstance(document, dict):
                document = {}
            mutate(document)
            temporary = path.with_suffix(path.suffix + '.tmp')
            temporary.write_text(json.dumps(document))
            temporary.replace(path)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def load_geometry(path, mode):
    path = Path(path)
    document = _locked_read(path)
    geometry = document.get(mode)
    if geometry is None and mode == 'full' and _valid(document):
        geometry = document  # Backward-compatible standalone flat layout.
    return dict(geometry) if _valid(geometry) else None


def save_geometry(path, mode, geometry):
    geometry = {key: int(geometry[key]) for key in _KEYS}

    def mutate(document):
        document[mode] = geometry
        if mode == 'full':
            document.update(geometry)  # Keep old flat readers compatible.

    _locked_merge_write(Path(path), mutate)


def load_compact(path):
    document = _locked_read(Path(path))
    return bool(document.get('compact', False))


def save_compact(path, value):
    def mutate(document):
        document['compact'] = bool(value)

    _locked_merge_write(Path(path), mutate)


def migrate_legacy(shared_path, legacy_paths):
    """One-time, idempotent: seed ``shared_path``'s "full" geometry from the
    newest legacy flat {x,y,width,height} file, WITHOUT ever overwriting a
    shared file that already exists (even a partially-populated one)."""
    shared_path = Path(shared_path)
    if shared_path.exists():
        return
    candidates = []
    for legacy in legacy_paths:
        legacy = Path(legacy)
        if legacy.exists():
            try:
                geometry = json.loads(legacy.read_text())
            except ValueError:
                continue
            if _valid(geometry):
                candidates.append((legacy.stat().st_mtime, geometry))
    if not candidates:
        return
    candidates.sort(key=lambda pair: pair[0])
    _, newest = candidates[-1]
    save_geometry(shared_path, 'full', newest)
