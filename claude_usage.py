"""Read-only usage query for the highest-priority stored Claude OAuth account."""
import argparse
import json
import sys
from agent.credential_pool import read_credential_pool
import agent.account_usage as account_usage
import anthropic_percent
anthropic_percent.install(account_usage)  # Anthropic utilization is already percent.
from agent.account_usage import _fetch_anthropic_account_usage
from hermes_cli.subcommands.usage import usage_snapshot_document
from account_selector import list_accounts

parser = argparse.ArgumentParser()
parser.add_argument('--list-accounts', action='store_true', help='Print stored account metadata only; no usage fetch')
parser.add_argument('--account-id', default=None, help='Fetch usage for this specific stored account instead of the highest-priority one')
args = parser.parse_args()

if args.list_accounts:
    print(json.dumps(list_accounts('anthropic')))
    raise SystemExit(0)

entries = sorted(read_credential_pool('anthropic'), key=lambda e: e.get('priority', 999))
usable = [e for e in entries if e.get('access_token') and e.get('auth_type') == 'oauth']
if args.account_id and args.account_id != 'default':
    entry = next((e for e in usable if e.get('id') == args.account_id), None)
else:
    entry = usable[0] if usable else None
if entry is None:
    print('Selected Claude account is unavailable', file=sys.stderr)
    raise SystemExit(1)
try:
    snapshot = _fetch_anthropic_account_usage(api_key=entry['access_token'])
    if not snapshot:
        raise RuntimeError('Usage unavailable')
    result = usage_snapshot_document(snapshot)
    # Stale-result guard: the caller diffs these against the request it made, so a
    # response that raced a selector change (or an old generation) is rejected rather
    # than silently rendered over the newly-chosen account.
    result['account_id'] = args.account_id or 'default'
    result['account_label'] = entry.get('label', 'Claude OAuth')
    print(json.dumps(result))
except Exception as error:
    # Avoid logging credentials or HTTP request headers.
    status = getattr(getattr(error, 'response', None), 'status_code', None)
    print('Claude quota fetch failed: ' + type(error).__name__ + (f' HTTP {status}' if status else ''), file=sys.stderr)
    raise SystemExit(1)
