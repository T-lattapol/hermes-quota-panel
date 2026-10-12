"""Explicitly confirmed Codex reset; dry-run is the default."""
import argparse
import json
from dataclasses import asdict
from agent.account_usage import fetch_account_usage, redeem_codex_reset_credit
from hermes_cli.subcommands.usage import usage_snapshot_document

parser = argparse.ArgumentParser()
parser.add_argument('--confirm', action='store_true', help='Consume one banked reset after UI confirmation')
parser.add_argument('--force', action='store_true', help='Explicitly allow a reset before quota exhaustion')
parser.add_argument('--account-id', default=None, help='Account currently selected in the panel; reset is refused when this is not the default account')
args = parser.parse_args()
if args.confirm and args.account_id not in (None, 'default'):
    # Never redeem a reset credit against the pool's default/active Codex account while the
    # panel is displaying a DIFFERENT selected account's usage — that would silently spend the
    # default account's banked credit for an action the user aimed at another account.
    print(json.dumps({'status': 'skipped_non_default', 'redeemed': False,
                       'message': 'Reset is only available while viewing the default Codex account. '
                                   'Switch the selector back to the default account to use a reset credit.'}))
    raise SystemExit(0)
if not args.confirm:
    snapshot = fetch_account_usage('openai-codex')
    if snapshot is None:
        raise SystemExit('Unable to fetch Codex quota')
    print(json.dumps({'dry_run': True, 'usage': usage_snapshot_document(snapshot)}))
else:
    result = redeem_codex_reset_credit(force=args.force)
    output = asdict(result)
    if result.redeemed:
        snapshot = fetch_account_usage('openai-codex')
        output['verified_usage'] = usage_snapshot_document(snapshot) if snapshot else None
    print(json.dumps(output))
