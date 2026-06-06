# python-pulsar-mouse-tool

A Python toolkit for the **Pulsar X2 v2 Mini** wireless mouse, with a **Wooting 80HE lightbar** battery indicator.

Supported hardware:
- Mouse: Pulsar X2 v2 Mini — wired and 1 kHz wireless dongle (VID `0x3710` PID `0x5406`)
- Keyboard: Wooting 80HE (PIDs `0x1400`–`0x1402`)

Both protocols were reverse-engineered via USB packet captures (Wireshark / USBPcap). This repository is mainly a record of that work and a reference for projects like [libratbag](https://github.com/libratbag/libratbag).

---

## Tools

### `mouse_battery_strip.py` — Battery → Lightbar bridge *(Windows)*

System tray app. Reads the Pulsar battery every 60 seconds and pushes the percentage to the Wooting 80HE lightbar Light Indicator, so the lightbar acts as a wireless mouse battery gauge.

Uses `hidapi` — no driver replacement needed for either device.

**One-time setup in Wootility:**

1. Lightbar → **Light Indicator** → add any data source (CPU works fine)
2. Style the gradient to taste (green = full, red = low is natural for battery)
3. Settings → **Background Service** → disable that data source so Wootility stops overwriting the value

**Run:**

```
pythonw mouse_battery_strip.py
```

Using `pythonw` avoids a console window. A coloured circle appears in the system tray — green above 50%, orange above 20%, red below.

**Tray menu:**
- **Refresh now** — poll immediately
- **Start with Windows** — toggle autostart via `HKCU\...\Run` (no admin needed)
- **Quit**

The poll interval is 60 seconds; change `POLL_INTERVAL` at the top of the script to adjust.

See [WOOTING_LIGHTBAR.md](WOOTING_LIGHTBAR.md) for the full reverse-engineered USB protocol.

---

### `pulsar_battery.py` — Standalone battery reader *(Windows / Linux / macOS)*

Prints battery status. Uses `hidapi`, no driver replacement needed.

```
$ python pulsar_battery.py
Battery:  72%
Voltage:  3980 mV
Charging: False
```

---

### `pulsar.py` — Mouse settings CLI *(Windows / Linux)*

Reads and writes on-device settings over USB via `pyusb`. An alternative to the official Pulsar Fusion software. Does not implement button remapping or macros.

**Linux setup:**

```
sudo cp 49-pulsar-mouse.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

**Windows setup:**

Place `libusb-1.0.dll` next to `pulsar.py` (download from [libusb.info](https://libusb.info)), or install libusb system-wide.

**Usage:**

```
$ python pulsar.py --help
usage: pulsar.py [-h] [--dpi DPI] [--dpi-mode DPI_MODE]
                 [--led-brightness LED_BRIGHTNESS] [--led-color LED_COLOR]
                 [--led-effect {off,steady,breathe}]
                 [--motion-sync {on,off}] [--lod-ripple {on,off}]
                 [--angle-snapping {on,off}]
                 [--polling-rate {1000,500,250,125}]
                 [--restore]
```

**Read current settings and battery:**

```
$ python pulsar.py
{
  "active_dpi_mode": 0,
  "active_profile": 0,
  "angle_snapping_enabled": false,
  "autosleep_seconds": 60,
  "debounce_milliseconds": 3,
  "dpi_modes": [
    { "dpi": 400,  "dpi_mode": 0, "led_color": "#2c2d2e" },
    { "dpi": 800,  "dpi_mode": 1, "led_color": "#303132" },
    { "dpi": 1600, "dpi_mode": 2, "led_color": "#343536" },
    { "dpi": 3200, "dpi_mode": 3, "led_color": "#38393a" }
  ],
  "led": { "effect": null, "enabled": false },
  "lod": { "mm": 1, "ripple_enabled": false },
  "motion_sync_enabled": true,
  "polling_rate_hz": 1000,
  "power": {
    "battery_millivolts": 3871,
    "battery_percent": 50,
    "connected": false
  }
}
```

**Change settings:**

```bash
python pulsar.py --dpi 800
python pulsar.py --polling-rate 500
python pulsar.py --led-effect breathe --led-color '#ff3300'
python pulsar.py --motion-sync off
python pulsar.py --restore          # factory defaults
```

---

## Installation

```
pip install hidapi pystray Pillow pyusb
```

`pystray` and `Pillow` are only needed for `mouse_battery_strip.py`. `pyusb` is only needed for `pulsar.py`.

---

## Protocol Documentation

- [WOOTING_LIGHTBAR.md](WOOTING_LIGHTBAR.md) — Reverse-engineered USB protocol for the Wooting 80HE lightbar data source command (`0x1F`), including packet structure, slot indexing, and how the Wooting Background Service communicates with the firmware
