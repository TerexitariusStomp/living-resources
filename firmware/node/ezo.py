# SPDX-License-Identifier: AGPL-3.0-or-later
# firmware/node/ezo.py — MicroPython seam for Atlas Scientific EZO
# carrier circuits, ported from the vendor's MIT-licensed
# Ezo_I2c_lib (oss-inventory.md). Thin seam: it reads whatever the
# circuit reports; range checks and unit policy live at the edge.

try:
    import utime as _t
except ImportError:
    import time as _t


def _sleep_ms(ms):
    if hasattr(_t, "sleep_ms"):
        _t.sleep_ms(ms)
    else:
        _t.sleep(ms / 1000)


class Ezo:
    """EZO circuit on I2C — 'R' + settle -> status byte + ASCII value.
    First CSV field only (a second field is the circuit's own temp
    input, not our calibrated water temp). A non-OK status or a
    non-numeric payload refuses the frame — never an invented value."""

    CMD_READ = b"R"
    OK = 1                       # EZO status codes: 1 ok, 2 pending,
                                 # 254 still processing, 255 no data

    def __init__(self, i2c, addr):
        self.i2c, self.addr = i2c, addr

    def read(self, settle_ms=1000):
        self.i2c.writeto(self.addr, self.CMD_READ)
        _sleep_ms(settle_ms)
        buf = self.i2c.readfrom(self.addr, 16)
        if not buf or buf[0] != self.OK:
            return None
        try:
            field = bytes(buf[1:]).split(b",")[0].strip(b"\x00 \r\n")
            return float(field)
        except ValueError:
            return None
