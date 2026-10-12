"""Pure formatters for the top-panel quota menus."""
import math
from runtime_paths import DISPLAY_ZONE, TIMEZONE_LABEL

def usage_bar(used):
    value = float(used)
    if not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError('Usage must be between 0 and 100')
    filled = max(1, int(value / 5 + 0.5)) if value else 0
    return '▰' * filled + '▱' * (20 - filled) + f'  {value:g}% used'

def usage_color(used):
    value = float(used)
    if not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError('Usage must be between 0 and 100')
    return 'red' if value >= 90 else 'amber' if value >= 70 else 'green'

def reset_credits(data):
    import re
    if data.get('provider') != 'openai-codex':
        return 0
    for detail in data.get('details', []):
        match = re.search(r'You have (\d+) resets? banked', detail)
        if match:
            return int(match.group(1))
    return 0

def reset_expiry_lines(data):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    if data.get('provider') != 'openai-codex':
        return []
    entries = [credit for credit in data.get('reset_credit_details', []) if credit.get('status') == 'available']
    entries.sort(key=lambda credit: credit.get('expires_at') or '9999')
    lines = []
    for index, credit in enumerate(entries, 1):
        value = credit.get('expires_at')
        if value:
            expiry = datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(DISPLAY_ZONE)
            lines.append(f'Reset {index} expires ' + expiry.strftime('%d %b %Y · %H:%M ') + TIMEZONE_LABEL)
        else:
            lines.append(f'Reset {index} expiry unavailable')
    return lines or ['Reset credit expiry unavailable' if reset_credits(data) else 'No reset credits available']

def is_menu_open_event(body):
    return isinstance(body, (tuple, list)) and len(body) >= 2 and body[0] == 0 and body[1] == 'opened'
