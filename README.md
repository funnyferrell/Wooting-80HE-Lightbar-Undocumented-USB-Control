# wooting-lightbar

Control the **Wooting 80HE LED bar** programmatically from Python, without
the Wooting RGB SDK and without conflicting with the Wootility Background
Service.

---

## Background

The Wooting RGB SDK does not expose the 80HE lightbar.  As of firmware 2.13,
Wooting's own changelog notes SDK lightbar support as a future feature.

The Wootility Background Service can drive the lightbar with live system
metrics (CPU %, RAM %, volume, etc.) via its "Light Indicator" feature.  This
library uses the same undocumented USB command (`0x1f`) discovered by capturing
USB traffic from the Background Service.

Full protocol details are in [WOOTING_LIGHTBAR.md](WOOTING_LIGHTBAR.md).

---

## Requirements

- Python 3.10+
- Wooting 80HE with Wootility installed

```
pip install hidapi
```

---

## Wootility setup (one-time)

The keyboard renders values using a Light Indicator effect configured in
Wootility.  The library controls the *value*; Wootility controls the *look*.

1. In Wootility: **Lightbar → Light Indicator → add a data source**
   (CPU, RAM, or Volume — the type doesn't matter, only its slot position)
2. Style the effect however you like
3. **Settings → Background Service → disable that data source**
   so the Background Service stops overwriting the values you push

---

## Usage

```python
from wooting_lightbar import send_lightbar_value

# Push a single value (0.0–100.0) to slot 0
send_lightbar_value(75.0)
```

For multiple updates or multiple slots:

```python
from wooting_lightbar import Lightbar

with Lightbar() as bar:
    bar.send(cpu_pct, slot=0)
    bar.send(ram_pct, slot=1)
```

See [example.py](example.py) for a runnable demo.

---

## API

### `send_lightbar_value(value, slot=0)`

Push a value to a lightbar data source slot.  Opens the HID device, writes
one packet, closes immediately.

| Parameter | Type  | Description |
|-----------|-------|-------------|
| `value`   | float | 0.0–100.0   |
| `slot`    | int   | Data source slot index (0 = first source added in Wootility) |

Raises `RuntimeError` if the keyboard is not found.

### `Lightbar` (context manager)

Keeps the HID device open across multiple `.send()` calls.  Prefer this
when updating several slots at once or sending values frequently.

### `find_wooting_path()`

Returns the raw HID path of the config interface, or `None`.  Useful if
you need direct device access.

---

## License

MIT
