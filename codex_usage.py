"""Codex quota snapshot with reset-credit expiry metadata; never redeems."""
import argparse
import json
from agent.credential_pool import read_credential_pool, PooledCredential
from agent.account_usage import fetch_account_usage, _resolve_codex_usage_credentials, _codex_backend_urls, _codex_headers, _get_json
from hermes_cli.auth_codex import _codex_pool_route_base_url
from hermes_cli.subcommands.usage import usage_snapshot_document
from account_selector import list_accounts

parser = argparse.ArgumentParser()
parser.add_argument('--list-accounts', action='store_true', help='Print stored account metadata only; no usage fetch')
parser.add_argument('--account-id', default=None, help='Fetch usage for this specific stored account instead of the default one')
args = parser.parse_args()

if args.list_accounts:
    print(json.dumps(list_accounts('openai-codex')))
    raise SystemExit(0)

# An explicit non-'default' selection must report THIS credential's usage, never silently
# fall back to the ambient/pool-selected one, and must never rotate/refresh/mutate it: the
# picker only reads one credential's metadata and quota.
explicit_token = None
explicit_base_url = None
selected_label = None
if args.account_id and args.account_id != 'default':
    entries = read_credential_pool('openai-codex')
    entry = next((e for e in entries if e.get('id') == args.account_id and e.get('auth_type') == 'oauth' and e.get('access_token')), None)
    if entry is None:
        raise SystemExit('Selected Codex account is unavailable')
    pooled = PooledCredential.from_dict('openai-codex', entry)
    explicit_token = pooled.runtime_api_key
    # Pool rows keep the canonical ChatGPT URL; a pooled gateway key must route to its own
    # host, not whatever the ambient default session is using (mirrors
    # ``_resolve_codex_usage_credentials``'s own pool tier, #121486).
    explicit_base_url = _codex_pool_route_base_url(pooled.runtime_base_url)
    selected_label = entry.get('label') or entry['id']

if explicit_token:
    # read_only=True: a 401 here is reported, never repaired — this per-credential read
    # must not rotate/refresh/bench a pool entry it does not own.
    snapshot = fetch_account_usage('openai-codex', base_url=explicit_base_url, api_key=explicit_token, read_only=True)
else:
    snapshot = fetch_account_usage('openai-codex')
if snapshot is None:
    raise SystemExit('Codex quota unavailable')
data = usage_snapshot_document(snapshot)
data['account_id'] = args.account_id or 'default'
data['account_label'] = selected_label or 'OpenAI Codex OAuth'
try:
    token, base, account = (
        _resolve_codex_usage_credentials(explicit_base_url, explicit_token) if explicit_token
        else _resolve_codex_usage_credentials(None, None)
    )
    credits = _get_json(_codex_backend_urls(base)[1], _codex_headers(token, account), timeout=15)
    data['reset_credit_details'] = [
        {key: credit.get(key) for key in ('status', 'expires_at', 'is_supported_by_plan', 'title')}
        for credit in credits.get('credits', [])
    ]
except Exception:
    data['reset_credit_details'] = []
    data['reset_credits_error'] = 'Reset credit expiry could not be fetched'
print(json.dumps(data))
