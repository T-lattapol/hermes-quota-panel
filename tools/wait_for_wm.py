"""Wait for the isolated headless test window manager to announce itself."""
import subprocess
import time

end = time.monotonic() + 15
while time.monotonic() < end:
    probe = subprocess.run(['xprop', '-root', '_NET_SUPPORTING_WM_CHECK'], text=True, capture_output=True)
    if 'window id #' in probe.stdout:
        break
    time.sleep(.1)
else:
    raise SystemExit('The test window manager did not become ready')
