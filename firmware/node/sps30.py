# SPDX-License-Identifier: AGPL-3.0-or-later
# firmware/node/sps30.py — MicroPython seam for the Sensirion SPS30,
# ported from the vendor's BSD-3 embedded-i2c-sps30 driver
# (oss-inventory.md). Thin seam: CRC-checks and unpacks the frame;
# calibration and evidence grading live at the edge.

try:
    import utime as _t
except ImportError:
    import time as _t


def _sleep_ms(ms):
    if hasattr(_t, "sleep_ms"):
        _t.sleep_ms(ms)
    else:
        _t.sleep(ms / 1000)


def crc8(data):
    """Sensirion CRC-8 (poly 0x31, init 0xFF); a mismatch refuses the frame."""
    crc = 0xFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0x31) & 0xFF if crc & 0x80 \
                  else (crc << 1) & 0xFF
    return crc


class Sps30:
    """SPS30 on I2C 0x69 (ENV-HEADS.md); read()->pm dict or None on fault."""

    ADDR = 0x69
    # start measurement, high-precision float format arg + its CRC
    CMD_MEASURE = b"\x00\x10\x03\x00" + \
        bytes([crc8(b"\x03\x00")])
    CMD_READ = b"\x03\x00"

    def __init__(self, i2c):
        self.i2c = i2c

    def read(self):
        self.i2c.writeto(self.ADDR, self.CMD_MEASURE)
        _sleep_ms(1100)                       # fan spin-up + first meas
        self.i2c.writeto(self.ADDR, self.CMD_READ)
        buf = self.i2c.readfrom(self.ADDR, 60)
        vals = []
        for i in range(10):
            w = buf[6 + i * 3: 6 + i * 3 + 2]
            if crc8(w) != buf[6 + i * 3 + 2]:
                return None                   # corrupt frame → refuse
            vals.append(((w[0] << 8) | w[1]) / 10)
        return {"pm1": vals[0], "pm2_5": vals[1],
                "pm4": vals[2], "pm10": vals[3]}
