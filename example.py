"""
example.py — minimal Wooting 80HE lightbar demo.

Sends a value to the lightbar every 5 seconds.
Replace get_value() with your own data source — CPU temperature,
mouse battery percentage, download speed, a countdown, anything
that maps to a 0–100 float.

See WOOTING_LIGHTBAR.md for full setup instructions.
"""

import time
from wooting_lightbar import send_lightbar_value


def get_value() -> float:
    """Return a value between 0.0 and 100.0.  Replace with your data source."""
    import psutil
    return psutil.cpu_percent(interval=None)


if __name__ == "__main__":
    print("Sending values to Wooting lightbar. Ctrl+C to stop.\n")
    while True:
        value = get_value()
        send_lightbar_value(value)
        print(f"{value:.1f}%")
        time.sleep(5)
