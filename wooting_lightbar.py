"""
wooting_lightbar.py — Control the Wooting 80HE LED bar.

Exposes the undocumented firmware command 0x1f, which pushes a 0–100 float
value to a lightbar data source slot.  The keyboard renders the value using
whatever Light Indicator effect is configured for that slot in Wootility.

See WOOTING_LIGHTBAR.md for full protocol documentation and Wootility setup.

Requirements:
    pip install hidapi
"""

import hid
import struct

__version__ = "1.0.0"
__all__ = ["find_wooting_path", "send_lightbar_value", "Lightbar"]

# ── Device identifiers ────────────────────────────────────────────────────────

WOOTING_VID       = 0x31e3
WOOTING_80HE_PIDS = [0x1400, 0x1401, 0x1402]  # base + two alt-PID variants
CFG_V3_USAGE_PAGE = 0xFF55                      # multi-report V3 (80HE)
CFG_USAGE_PAGE    = 0x1337                      # V1/V2 fallback


# ── Internal ──────────────────────────────────────────────────────────────────

def _make_cmd(value: float, slot: int) -> bytes:
    """Build the 33-byte cmd 0x1f packet. See WOOTING_LIGHTBAR.md."""
    f = struct.pack('<f', float(value))
    cmd = bytearray(33)
    cmd[0]  = 0x01   # HID report ID (multi-report V3)
    cmd[1]  = 0xD1   # magic byte (V3 variant)
    cmd[2]  = 0xDA   # magic byte
    cmd[3]  = 0x1F   # command: data source update
    cmd[4]  = 0x09   # fixed wrapper
    cmd[5]  = 0x00
    cmd[6]  = 0x0A
    cmd[7]  = 0x07
    cmd[8]  = 0x08   # protobuf field 1 tag (varint = slot index)
    cmd[9]  = slot
    cmd[10] = 0x15   # protobuf field 2 tag (32-bit fixed = f32)
    cmd[11] = f[0]   # float bytes, little-endian
    cmd[12] = f[1]
    cmd[13] = f[2]
    cmd[14] = f[3]
    return bytes(cmd)


# ── Public API ────────────────────────────────────────────────────────────────

def find_wooting_path() -> bytes | None:
    """
    Return the HID path for the Wooting 80HE config interface, or None.

    Checks all known 80HE PIDs and returns the first interface whose
    usage page matches the V3 (0xFF55) or V1/V2 (0x1337) config interface.
    """
    for pid in WOOTING_80HE_PIDS:
        for info in hid.enumerate(WOOTING_VID, pid):
            if info['usage_page'] in (CFG_V3_USAGE_PAGE, CFG_USAGE_PAGE):
                return info['path']
    return None


def send_lightbar_value(value: float, slot: int = 0) -> None:
    """
    Push a value to a Wooting 80HE lightbar data source slot.

    Opens the HID device, writes one packet, and closes immediately.
    Use the Lightbar context manager if you need to send multiple updates
    in quick succession.

    Parameters
    ----------
    value : float
        0.0–100.0.  The firmware renders this using the Light Indicator
        effect configured for the slot in Wootility.
    slot : int
        Data source slot index.  Corresponds to the order in which sources
        were added to the Light Indicator in Wootility (0 = first).

    Raises
    ------
    RuntimeError
        If the keyboard config interface cannot be found.
    """
    path = find_wooting_path()
    if path is None:
        raise RuntimeError(
            "Wooting 80HE config interface not found. "
            "Is the keyboard connected?"
        )
    dev = hid.device()
    dev.open_path(path)
    try:
        dev.write(_make_cmd(value, slot))
    finally:
        dev.close()


class Lightbar:
    """
    Context manager for sending multiple updates without reopening the device.

    Prefer this over repeated send_lightbar_value() calls when updating
    several slots at once or sending values at high frequency.

    Example
    -------
    >>> with Lightbar() as bar:
    ...     bar.send(cpu_pct, slot=0)
    ...     bar.send(ram_pct, slot=1)
    """

    def __init__(self) -> None:
        self._dev: hid.device | None = None

    def __enter__(self) -> "Lightbar":
        path = find_wooting_path()
        if path is None:
            raise RuntimeError(
                "Wooting 80HE config interface not found. "
                "Is the keyboard connected?"
            )
        self._dev = hid.device()
        self._dev.open_path(path)
        return self

    def __exit__(self, *_) -> None:
        if self._dev is not None:
            self._dev.close()
            self._dev = None

    def send(self, value: float, slot: int = 0) -> None:
        """Push a value (0.0–100.0) to a lightbar slot."""
        if self._dev is None:
            raise RuntimeError("Lightbar is not open (use as a context manager)")
        self._dev.write(_make_cmd(value, slot))
