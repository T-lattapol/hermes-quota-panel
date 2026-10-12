"""Read-only account metadata for the quota panel's account selector.

Never returns a token, header, or other credential value — only id/label/
priority/default-ness. The caller decides which account's USAGE to display;
it never changes the pool's active account, priorities, cooldowns or any
bot-profile credential selection.
"""
try:
    from agent.credential_pool import read_credential_pool
except ImportError:  # pragma: no cover - exercised under the GTK system python
    def read_credential_pool(provider_id=None):
        return []

SINGLETON_ID = 'default'


def _usable(entry):
    return entry.get('auth_type') == 'oauth' and bool(entry.get('access_token'))


def _public(entry, is_default):
    return {
        'id': entry['id'],
        'label': entry.get('label') or entry['id'],
        'priority': entry.get('priority', 999),
        'is_default': is_default,
    }


def list_accounts(provider):
    """Usable stored OAuth accounts for ``provider``, lowest priority first.

    Falls back to one singleton pseudo-account when the pool has none, so the
    selector always offers at least the ambient/default login.
    """
    entries = sorted((e for e in read_credential_pool(provider) if _usable(e)),
                      key=lambda e: e.get('priority', 999))
    if not entries:
        return [{'id': SINGLETON_ID, 'label': 'Default account', 'priority': 0, 'is_default': True}]
    return [_public(entry, index == 0) for index, entry in enumerate(entries)]


def default_account_id(provider):
    accounts = list_accounts(provider)
    return next((a['id'] for a in accounts if a['is_default']), accounts[0]['id'])


def is_default_selection(provider, account_id):
    """True when ``account_id`` (or None, meaning "not chosen yet") refers to
    the same account the provider would use with no explicit selection."""
    if account_id is None:
        return True
    return account_id == default_account_id(provider)
