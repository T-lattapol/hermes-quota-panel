"""Correct Hermes' Anthropic quota scaling inside the helper process only.

Anthropic's OAuth usage endpoint reports ``utilization`` in percent (2.0 means 2%).
Hermes scales any value <= 1 as a fraction, so 1% is displayed as 100%.
"""


def install(account_usage):
    original = account_usage._usage_windows
    if getattr(original, '_quota_panel_percent', False):
        return

    def percent_windows(*args, **kwargs):
        kwargs['fraction'] = False
        return original(*args, **kwargs)

    percent_windows._quota_panel_percent = True
    account_usage._usage_windows = percent_windows
