# SPDX-License-Identifier: AGPL-3.0-or-later
# firmware/node/adpcm.py — bounded LoRa eco-audio clips.
# .auc is derived, not archival: FIR first, then 6:1 decimation.

try:
    import ujson as json
except ImportError:
    import json

CLIP_SECONDS = 0.5
CLIP_RATE = 8000
FIR = (1, 2, 4, 6, 7, 6, 4, 2, 1)
FIR_SUM = 33
DECIMATE = 6
STEP = (7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963, 1060, 1166, 1282, 1411,
        1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767)
IDX = (-1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8)


def _s16(b, i):
    v = b[i] | (b[i + 1] << 8)
    return v - 65536 if v & 0x8000 else v


def decimate(pcm, src_rate=48000):
    ns = min(len(pcm) // 2, int(src_rate * CLIP_SECONDS))
    out = bytearray()
    for center in range(4, ns - 4, DECIMATE):
        acc = 0
        for j, coef in enumerate(FIR):
            acc += coef * _s16(pcm, 2 * (center + j - 4))
        v = max(-32768, min(32767, acc // FIR_SUM))
        out += bytes((v & 0xFF, (v >> 8) & 0xFF))
    return bytes(out)


def encode(pcm16):
    pred, idx, high = 0, 0, False
    out = bytearray()
    for i in range(0, len(pcm16) - 1, 2):
        sample, step = _s16(pcm16, i), STEP[idx]
        diff = sample - pred
        code = 0
        if diff < 0:
            code, diff = 8, -diff
        vpd = step >> 3
        if diff >= step:
            code, diff, vpd = code | 4, diff - step, vpd + step
        if diff >= step >> 1:
            code, diff, vpd = code | 2, diff - (step >> 1), vpd + (step >> 1)
        if diff >= step >> 2:
            code, vpd = code | 1, vpd + (step >> 2)
        pred = max(-32768, min(32767, pred - vpd if code & 8 else pred + vpd))
        idx = max(0, min(88, idx + IDX[code]))
        if high:
            out[-1] |= code << 4
        else:
            out.append(code)
        high = not high
    return bytes(out)


def clip_packet(pcm, node, name):
    small = decimate(pcm)
    if not small:
        return None
    meta = {"kind": "audio-clip", "node": node, "name": name,
            "codec": "ima-adpcm-v1", "rate": CLIP_RATE,
            "src_rate": 48000, "seconds": len(small) // 2 / CLIP_RATE,
            "filter": "fir9-sum33-dec6"}
    m = json.dumps(meta, separators=(",", ":")).encode()
    return bytes((len(m) >> 8, len(m) & 0xFF)) + m + encode(small)
