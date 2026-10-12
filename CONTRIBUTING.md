# Contributing

1. Keep app state out of the checkout and keep helper processes separate from GTK's interpreter.
2. Add a failing offline test before changing behavior. Network/credential tests must remain opt-in.
3. Preserve the reset confirmation and non-default-account guards in both UI and controller.
4. Exercise compact/full visibility after update, failure, hide/show, and provider handoff.
5. Use the real GTK main loop for native resizing; never weaken a geometry test simply because of timing.
6. Run the offline tests, JavaScript checks, syntax checks, and publication audit.
7. Review every file staged for publication. Never upload a screen capture containing real account information.

This viewer relies on internal Hermes account-usage interfaces; compatibility changes should be checked by `doctor.py` and backed by tests.
