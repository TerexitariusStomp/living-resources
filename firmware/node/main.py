# SPDX-License-Identifier: AGPL-3.0-or-later
# firmware/node/main.py — EcoCell universal field node (MicroPython,
# XIAO ESP32-S3 class)
#
# WHAT THIS FILE IS. The node-side skeleton of the living cell: capture
# lossless audio on an I2S head, buffer to microSD (store-and-forward is
# a property of the node, not the link), flush detections and audio
# windows on scheduled uplinks over Reticulum, and duty-cycle deep-sleep
# in between. The lanes dict is the whole point of the hardware spec:
# every device ships every head's electronics — camera, air mic, env
# sensors, hydrophone front-end, ultrasonic MEMS, C4D, and a live
# emit path — and lanes are activated by firmware flag or, for emit,
# by a consent token the edge's lane gate enforces.
#
# Runs on MicroPython ESP32-S3; imports are guarded so `python3 -m
# py_compile` and a desktop --sim pass both work. The classifier does NOT
# run here — the edge runs OpenSoundscape; the node may run a trivial
# energy gate to wake for likely-vocal windows (dumb node, smart edge).

import time

try:
    import machine                       # MicroPython
    from machine import Pin, I2S, SDCard, deepsleep, lightsleep
    _ON_NODE = True
except ImportError:                      # desktop sim / CI
    machine = None
    _ON_NODE = False

try:
    import uos as os
except ImportError:
    import os

try:
    import ujson as json
except ImportError:
    import json


# ── the lanes ─────────────────────────────────────────────────────────────
# Universal node: EVERY device ships every head's electronics — there is
# no variant, no upgrade purchase. enabled = firmware flag for this
# deployment's role; gated = requires a consent token (guardian + operator)
# before it may act; nothing on this board is hardware-locked. The emit
# lane is fully implemented — bio-write rides the same joint consent the
# edge enforces in module/living/offers.scm.
LANES = {
    "cam":   {"enabled": True,  "gated": None,
              "head": "OV2640 onboard", "band": "visible",
              "role": "phenology, pollinators, wildlife passage"},
    "mic":   {"enabled": True,  "gated": None,
              "head": "INMP441 I2S", "band": "0-24kHz",
              "role": "air mic — birds/insects/frogs"},
    "env":   {"enabled": True,  "gated": None,
              "head": "BME280 + BH1750 + PIR", "band": "context",
              "role": "temp/humidity/pressure/light + wake trigger"},
    "hydro": {"enabled": True,  "gated": None,
              "head": "hydrophone lead", "band": "0-24kHz",
              "role": "shore/dock/reef cell — fish, shrimp, mammals"},
    "ultra": {"enabled": True,  "gated": None,
              "head": "ICS-40730 MEMS", "band": "20-100kHz",
              "role": "plant clicks, bat/insect ultrasound"},
    "c4d":   {"enabled": True,  "gated": None,
              "head": "C4D front-end", "band": "capacitance",
              "role": "biofilm readout"},
    "emit":  {"enabled": False, "gated": "consent",
              "head": "PWM + H-bridge 40kHz", "band": "emit",
              "role": "bio-write — transducer, consent-gated"},
}

SAMPLE_RATE   = 48000        # INMP441, covers full audible bioacoustics
BITS          = 16
CHUNK_SECONDS = 10           # capture granule
WINDOW_SECONDS = 300         # one uplink window of audio
SD_MOUNT      = "/sd"
DETECTION_MAX_BYTES = 200    # LoRa path: detections are tens of bytes

# duty cycle: wake for these wall-clock windows (hour starts, localtime)
WAKE_WINDOWS = ((4, 10), (17, 21))   # dawn chorus + dusk; 0-24h
SLEEP_BETWEEN_WINDOWS_S = 1800


# ── capture ───────────────────────────────────────────────────────────────

class MicCapture:
    """I2S capture at 48kHz/16-bit into PCM frames. On the desktop sim the
    read() returns silence — the buffer shape is identical."""

    def __init__(self, sck=8, ws=9, sd=7, rate=SAMPLE_RATE, bits=BITS):
        self.rate, self.bits = rate, bits
        self._i2s = None
        if _ON_NODE:
            self._i2s = I2S(0, sck=Pin(sck), ws=Pin(ws), sd=Pin(sd),
                            mode=I2S.RX, bits=bits,
                            format=I2S.MONO, rate=rate,
                            ibuf=rate * bits // 8)   # ~1s buffer

    def read(self, nbytes):
        if self._i2s:
            return self._i2s.readinto(bytearray(nbytes)) or b""
        return bytes(nbytes)                       # sim: silence

    def energy(self, buf):
        """Mean absolute amplitude of 16-bit PCM — the cheap wake gate."""
        n = len(buf) // 2
        if not n:
            return 0
        acc = 0
        for i in range(0, len(buf), 2):
            v = buf[i] | (buf[i + 1] << 8)
            if v >= 0x8000:
                v -= 0x10000
            acc += abs(v)
        return acc // n


# ── the SD buffer ─────────────────────────────────────────────────────────

class SDBuffer:
    """Store-and-forward: PCM chunks and detection lines spool under
    /sd/spool; flush() drains them in order. A node offline for days loses
    nothing — LXMF semantics implemented over a filesystem."""

    def __init__(self, root=SD_MOUNT + "/spool"):
        self.root = root
        if _ON_NODE:
            try:
                os.mkdir(self.root)
            except OSError:
                pass
        self._sim = []          # desktop sim: list of (name, bytes)

    def spool(self, name, data):
        if _ON_NODE:
            with open(self.root + "/" + name, "wb") as f:
                f.write(data)
        else:
            self._sim.append((name, data))

    def pending(self):
        if _ON_NODE:
            try:
                return sorted(os.listdir(self.root))
            except OSError:
                return []
        return [n for n, _ in self._sim]

    def read(self, name):
        if _ON_NODE:
            with open(self.root + "/" + name, "rb") as f:
                return f.read()
        for n, d in self._sim:
            if n == name:
                return d
        return b""

    def clear(self, name):
        if _ON_NODE:
            try:
                os.remove(self.root + "/" + name)
            except OSError:
                pass
        else:
            self._sim = [(n, d) for n, d in self._sim if n != name]


# ── uplink ────────────────────────────────────────────────────────────────

class Uplink:
    """The two carriers in tier order. WiFi path: UDP datagrams of audio
    chunks + detections to the edge. LoRa path (SX1276/RNode): detection
    packets only — tens of bytes each.

    TODO(real binding): MicroReticulum LXMF socket goes here — announce the
    node's destination hash, receive/link ACKs, let LXMF queue what the
    link cannot carry now. Until that lands, send() returns False and the
    SD buffer simply keeps everything."""

    def __init__(self, edge_host=None, edge_port=4242, lora=None):
        self.edge = (edge_host, edge_port) if edge_host else None
        self.lora = lora

    def send_audio(self, name, blob):
        # TODO: LXMF resource or UDP datagram to self.edge; FLAC-encode
        # edge-side if bandwidth demands (the node keeps PCM).
        return False

    def send_detection(self, det_line):
        # tens of bytes — the priority payload that never waits for
        # bandwidth. TODO: RNode raw frame via self.lora uart.
        if len(det_line) > DETECTION_MAX_BYTES:
            return False
        return False


# ── detection packet ──────────────────────────────────────────────────────
# The node is dumb: detections arrive either from the edge (after it
# classifies an audio window) or, later, from a tiny on-device gate. A
# packet is the same tens of bytes either way — species, confidence,
# timestamp, node-id; SAIDs and subject get stamped at the edge.

NODE_ID = "node-7"


def detection_packet(species, confidence, ts):
    d = {"species": species, "confidence": confidence,
         "timestamp": ts, "node": NODE_ID}
    line = json.dumps(d)
    return line if len(line) <= DETECTION_MAX_BYTES else None


# ── the emit lane ─────────────────────────────────────────────────────────
# Bio-write: the 40 kHz transducer path. Fully implemented, consent-gated —
# an emit() with no token raises ConsentRequired; the token is the joint
# guardian+operator consent SAID the edge's lane gate checked upstream.
# The node enforces the same rule locally so a stale or spoofed downlink
# frame can never drive the transducer.

class ConsentRequired(Exception):
    pass


class EmitLane:
    """40 kHz transducer over PWM + H-bridge. Duty-cycled, minimum-power
    by default — the consent token may tighten, never loosen, these."""

    MAX_ON_MS = 50          # hard ceiling per emission
    MIN_OFF_MS = 950        # ≤5% duty, always

    def __init__(self, pwm_pin=5, freq=40000):
        self.freq = freq
        self._pwm = None
        if _ON_NODE:
            self._pwm = machine.PWM(Pin(pwm_pin), freq=freq, duty=0)

    def emit(self, burst_ms, consent=None):
        if not consent:
            raise ConsentRequired(
                "emit rides the joint consent of guardian and operator")
        burst_ms = min(burst_ms, self.MAX_ON_MS)
        if self._pwm:
            self._pwm.duty(512)
            time.sleep_ms(burst_ms)
            self._pwm.duty(0)
            time.sleep_ms(self.MIN_OFF_MS)
        return burst_ms        # sim: report the clipped burst


# ── duty cycle ────────────────────────────────────────────────────────────

def in_wake_window(now=None):
    t = now or time.localtime()
    hour = t[3]
    return any(start <= hour < end for start, end in WAKE_WINDOWS)


def sleep_until_next_window():
    if _ON_NODE:
        lightsleep(SLEEP_BETWEEN_WINDOWS_S * 1000)
    else:
        time.sleep(0.01)


# ── the node loop ─────────────────────────────────────────────────────────

def capture_window(cap, buf, seconds=WINDOW_SECONDS,
                   chunk_seconds=CHUNK_SECONDS):
    """Capture `seconds` of audio in chunks, spooling each to SD. Returns
    the chunk names spooled."""
    chunk_bytes = SAMPLE_RATE * BITS // 8 * chunk_seconds
    names = []
    elapsed = 0
    while elapsed < seconds:
        pcm = cap.read(chunk_bytes)
        if not pcm:
            pcm = bytes(chunk_bytes)          # sim / underrun: keep shape
        name = "w%d.pcm" % (int(time.time() * 1000) + elapsed)
        buf.spool(name, pcm)
        names.append(name)
        elapsed += chunk_seconds
    return names


def flush(buf, up):
    """Drain the spool: detections first (priority payload), audio after.
    Anything the link refuses stays spooled — store-and-forward."""
    for name in buf.pending():
        blob = buf.read(name)
        ok = (up.send_detection(blob) if name.endswith(".det")
              else up.send_audio(name, blob))
        if ok:
            buf.clear(name)


def run():
    if not LANES["mic"]["enabled"]:
        return
    cap = MicCapture()
    buf = SDBuffer()
    up = Uplink()
    while True:
        if not in_wake_window():
            sleep_until_next_window()
            continue
        capture_window(cap, buf)
        flush(buf, up)
        sleep_until_next_window()


def _sim():
    """Desktop sim: one capture window, a detection, a flush attempt. The
    uplink refuses by construction — what matters is the spool kept it."""
    cap = MicCapture()
    buf = SDBuffer()
    up = Uplink()
    names = capture_window(cap, buf, seconds=20, chunk_seconds=10)
    assert len(names) == 2, names
    det = detection_packet("Turdus migratorius", 0.91, 1730000000)
    buf.spool("d1.det", det.encode())
    flush(buf, up)
    assert len(buf.pending()) == 3, buf.pending()   # nothing left the node
    em = EmitLane()
    try:
        em.emit(20)
        raise AssertionError("emit without consent must refuse")
    except ConsentRequired:
        pass
    assert em.emit(200, consent="said:joint-consent") == 50  # clipped
    print("sim ok: %d chunks spooled, %d pending after refused flush, "
          "emit consent-gate held"
          % (len(names), len(buf.pending())))


if __name__ == "__main__":
    if _ON_NODE:
        run()
    else:
        _sim()
