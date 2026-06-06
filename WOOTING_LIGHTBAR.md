# Wooting 80HE Lightbar — Undocumented USB Control

This document describes how to programmatically control the Wooting 80HE's LED
bar (lightbar) from a host application, bypassing the Wooting RGB SDK and
Wootility's Background Service.

---

## Background

The Wooting RGB SDK exposes `wooting_rgb_direct_set_key(row, col, r, g, b)` for
per-key LED control. The 80HE lightbar is **not** addressable through this API.
As of firmware 2.13, Wooting's own changelog confirms this is an intentional
limitation with a note that SDK lightbar support is planned for a future release.

The Wootility Background Service (introduced in Wootility 5.2, a separate
`WootingBackgroundService.exe` process) can drive the lightbar with live system
metrics (CPU %, RAM %, volume, etc.) via its "Light Indicator" feature. This
document covers how that communication works at the USB level.

---

## Architecture

```
Wootility (Electron/WebView)
    │  gRPC-Web over HTTP  (localhost:50052)
    ▼
Wooting Background Service  (Rust + Tauri, ~5 MB RAM)
    │  HID interrupt write  (USB)
    ▼
Wooting 80HE firmware
    │
    ▼
Lightbar (10 LEDs)
```

The Background Service exposes two gRPC services on `localhost:50052`
(no TLS, reflection disabled):

| Service | Methods |
|---------|---------|
| `wooting_service.WootilityService` | `Heartbeat`, `CheckForUpdates`, `TriggerUpdate`, `GetAutoStartEnabled`, `SetAutoStartEnabled`, `OpenLogFolder` |
| `data_source_manager_service.DataSourceManagerCommunicationService` | `GetAllDataPointInfo`, `ListenToDataPointUpdates`, `GetAllDataSources`, `SetDataSourceEnabled` |

The data source manager collects metrics from internal providers
(`source_volume`, `source_battery`, `source_discord`, `source_system_info`)
and pushes current values to the keyboard at a regular interval.

---

## USB Protocol

The keyboard presents a HID interface with usage page `0xFF55`
(the V3 multi-report config interface). Data is sent as **interrupt OUT**
transfers via `hid_write()`.

### Command 0x1f — Data Source Update

All lightbar value updates use command `0x1f`. The packet is **33 bytes**:

```
Offset  Len  Value         Description
------  ---  -----------   ---------------------------------------------------
0       1    0x01          HID report ID (multi-report V3)
1       2    0xD1 0xDA     Wooting magic bytes (V3 variant; V1/V2 uses 0xD0 0xDA)
3       1    0x1F          Command: data source update
4       4    09 00 0A 07   Fixed wrapper (constant across all data sources)
8       1    0x08          Protobuf field 1 tag (varint)
9       1    slot          Data source slot index (0 = first, 1 = second, …)
10      1    0x15          Protobuf field 2 tag (32-bit fixed)
11      4    <f32 LE>      Current value as IEEE 754 float, little-endian, 0.0–100.0
15      18   0x00…         Zero padding
```

The **slot** byte maps to the order in which data sources are added to the
lightbar Light Indicator effect in Wootility. If only one source is configured
it occupies slot 0.

### Example — 75%

```
01 D1 DA 1F 09 00 0A 07 08 00 15 00 00 96 42 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
```

`struct.pack('<f', 75.0)` → `\x00\x00\x96\x42` at bytes 11–14.

For clean integer percentages the low two bytes of the float are always `0x00`,
so only bytes 13–14 vary across the 0–100 range.

---

## Python Implementation

```python
import hid, struct

WOOTING_VID       = 0x31e3
WOOTING_80HE_PIDS = [0x1400, 0x1401, 0x1402]
CFG_V3_USAGE_PAGE = 0xFF55
CFG_USAGE_PAGE    = 0x1337   # older V1/V2 devices


def find_wooting_path():
    for pid in WOOTING_80HE_PIDS:
        for info in hid.enumerate(WOOTING_VID, pid):
            if info['usage_page'] in (CFG_V3_USAGE_PAGE, CFG_USAGE_PAGE):
                return info['path']
    return None


def send_lightbar_value(value_pct: float, slot: int = 0):
    """Push a 0–100 float value to a lightbar data source slot."""
    f = struct.pack('<f', float(value_pct))
    cmd = bytearray(33)
    cmd[0]  = 0x01
    cmd[1]  = 0xD1
    cmd[2]  = 0xDA
    cmd[3]  = 0x1F
    cmd[4]  = 0x09
    cmd[5]  = 0x00
    cmd[6]  = 0x0A
    cmd[7]  = 0x07
    cmd[8]  = 0x08
    cmd[9]  = slot
    cmd[10] = 0x15
    cmd[11] = f[0]
    cmd[12] = f[1]
    cmd[13] = f[2]
    cmd[14] = f[3]

    path = find_wooting_path()
    if path is None:
        raise RuntimeError("Wooting 80HE config interface not found")

    dev = hid.device()
    dev.open_path(path)
    try:
        dev.write(bytes(cmd))
    finally:
        dev.close()
```

Requires [`hidapi`](https://pypi.org/project/hidapi/) (`pip install hidapi`).

---

## Wootility Setup

For the keyboard to render a pushed value, the lightbar must be configured with
a Light Indicator effect in Wootility:

1. Open Wootility → Lightbar → **Light Indicator**
2. Add any data source (CPU, RAM, Volume) — this source defines the visual style
   (bar shape, colours, gradient). The specific source type does not matter;
   only the slot index (order added) matters at the USB level.
3. Optionally: go to **Settings → Background Service** and disable that data
   source so the Background Service stops overwriting the value your application
   pushes.

The firmware renders whatever float value (0.0–100.0) was last written to a
slot using the visual effect configured for that slot in the active profile.

---

## Notes

- **Multi-process access**: On Windows, HID devices can be opened by multiple
  processes simultaneously. The Background Service and a third-party application
  can both hold handles to the config interface.
- **V3 vs V1/V2**: The 80HE uses the V3 multi-report interface (`0xFF55`). The
  magic byte is `0xD1` (V3) rather than `0xD0` (V1/V2). The RGB SDK's
  `wooting-usb.h` header defines both usage pages.
- **Value scale**: The firmware expects 0.0–100.0, matching the percentage scale
  used by all built-in data sources. Values outside this range are untested.
- **Discovery method**: Command 0x1f and its structure were found by capturing
  USB traffic (USBPcap + Wireshark) while the Background Service was running
  with an active Light Indicator effect, then comparing packets across multiple
  data source configurations to isolate the slot index byte.
