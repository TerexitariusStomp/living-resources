# SPDX-License-Identifier: AGPL-3.0-or-later
# tools/edge/adpcm.py — decode the node's AUC1 IMA-ADPCM clip format.

import json
import os
import struct
import wave

STEP = (7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34,
        37, 41, 45, 50, 55, 60, 66, 73, 80, 88, 97, 107, 118, 130, 143,
        157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494,
        544, 598, 658, 724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552,
        1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428,
        4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487,
        12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086,
        29794, 32767)
IDX = (-1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8)


def decode_payload(payload):
    """AUC spool payload → (metadata, packed ADPCM)."""
    if len(payload) < 4:
        return None
    mlen = (payload[0] << 8) | payload[1]
    if len(payload) < 2 + mlen:
        return None
    try:
        meta = json.loads(payload[2:2 + mlen].decode())
    except (ValueError, UnicodeDecodeError):
        return None
    if meta.get("codec") != "ima-adpcm-v1":
        return None
    return meta, payload[2 + mlen:]


def decode_adpcm(data):
    """4-bit IMA-ADPCM → s16le mono bytes."""
    pred, idx = 0, 0
    out = bytearray()
    for byte in data:
        for code in (byte & 0x0F, byte >> 4):
            step = STEP[idx]
            vpd = step >> 3
            if code & 4:
                vpd += step
            if code & 2:
                vpd += step >> 1
            if code & 1:
                vpd += step >> 2
            pred = pred - vpd if code & 8 else pred + vpd
            pred = max(-32768, min(32767, pred))
            idx = max(0, min(88, idx + IDX[code]))
            out += struct.pack("<h", pred)
    return bytes(out)


def decode_clip(payload):
    parsed = decode_payload(payload)
    if parsed is None:
        return None
    meta, packed = parsed
    return meta, decode_adpcm(packed)


def write_wav(path, meta, pcm):
    with wave.open(path, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(int(meta.get("rate", 8000)))
        wav.writeframes(pcm)
    with open(path, "r+b") as fh:
        os.fsync(fh.fileno())
