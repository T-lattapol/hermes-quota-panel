# Contributing

1. Keep app state out of the checkout and keep helper processes separate from GTK's interpreter.
2. Add a failing offline test before changing behavior. Network/credential tests must remain opt-in.
3. Preserve the reset confirmation and non-default-account guards in both UI and controller.
4. Exercise compact/full visibility after update, failure, hide/show, and provider handoff.
5. Use the real GTK main loop for native resizing; never weaken a geometry test simply because of timing.
6. Run the offline tests, JavaScript checks, syntax checks, and publication audit.
7. Review every file staged for publication. Never upload a screen capture containing real account information.

## Repository layout

- Root Python modules: application and installation entry points.
- `tests/`: offline tests, opt-in live integration tests, and synthetic fixtures.
- `tools/`: CI runner, publication audit, and reproducible demo screenshots.
- `docs/images/`: screenshots containing sample data only.
- `gnome-extension/` and `icons/`: optional desktop integration and artwork.

Run offline tests from the repository root:

```sh
xvfb-run -a /usr/bin/python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/test_direct_click.mjs
python3 tools/check_publish.py
```

This viewer relies on internal Hermes account-usage interfaces; compatibility changes should be checked by `doctor.py` and backed by tests.
