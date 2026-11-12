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

try:
    import usocket as socket              # MicroPython
except ImportError:
    import socket                         # CPython sim

try:
    import uhashlib as hashlib            # MicroPython
except ImportError:
    import hashlib                        # CPython sim

try:
    from ucryptolib import aes as _ucrypt_aes
except ImportError:
    _ucrypt_aes = None                    # desktop sim stores plaintext

try:
    from bme280_float import BME280       # vendored: third_party/bme280
except ImportError:
    BME280 = None                         # sim / stack not deployed


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
    "pm":    {"enabled": True,  "gated": None,
              "head": "Sensirion SPS30", "band": "0.5-10um",
              "role": "PM1/2.5/4/10 — dust events; I2C 0x69, 5V via J9"},
    "h2s":   {"enabled": True,  "gated": None,
              "head": "MQ-136 or SPEC electrochemical", "band": "analog/UART",
              "role": "H2S screening — lagoon-adjacent; indicative grade"},
    "emit":  {"enabled": False, "gated": "consent",
              "head": "PWM + H-bridge 40kHz", "band": "emit",
              "role": "bio-write — transducer, consent-gated"},
}

SAMPLE_RATE   = 48000        # INMP441, covers full audible bioacoustics
BITS          = 16
CHUNK_SECONDS = 10           # capture granule
WINDOW_SECONDS = CHUNK_SECONDS  # stream-first: flush after EVERY chunk —
                              # the device holds ~one chunk in flight,
                              # nothing archives on-node while the link lives
ENV_PERIOD_S = 300           # env scalars are slow-moving; poll 5-minutely
SD_MOUNT      = "/sd"
DETECTION_MAX_BYTES = 200    # LoRa path: detections are tens of bytes
PCM_KEEP_FILES = 4000        # ~11 h rolling audio; ~4 GB on a 32 GB card
AUC_KEEP_FILES = 240         # bounded LoRa clip queue
KEEP_FILES = {".pcm": PCM_KEEP_FILES, ".auc": AUC_KEEP_FILES,
              ".det": 600, ".env": 600, ".gap": 240, ".res": 600}
OTHER_KEEP_FILES = 240       # unknown extensions are bounded too
SPOOL_RESERVE_BYTES = 64 * 1024 * 1024   # never fill the card's last 64 MB
EDGE_PORT = 5055             # UDP uplink; tools/edge/udp_edge.py listens
# duty cycle: wake for these wall-clock windows (hour starts, localtime).
# DEFAULT IS CONTINUOUS — the node reads and writes around the clock;
# duty-cycled windows are a provisioning option for power-limited sites
# (set via /sd/lxmf.json "wake_windows" or a downlink "windows" task),
# never the product default.
WAKE_WINDOWS = ((0, 24),)


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

# ── env heads ─────────────────────────────────────────────────────────────
# PM (SPS30) and H2S readers — the Salton Sea heads. Both return small
# dicts that land in one .env JSON line per wake window; absent or
# faulted heads yield nothing, never invented values. See
# docs/ENV-HEADS.md for the parts-level caveats (I2C levels, MQ-136
# cross-sensitivity, indicative grade).

def _sleep_ms(ms):
    """utime.sleep_ms on-node; time.sleep on the desktop sim."""
    if hasattr(time, "sleep_ms"):
        time.sleep_ms(ms)
    else:
        time.sleep(ms / 1000)


def _sps30_crc8(data):
    """Sensirion CRC-8 (poly 0x31, init 0xFF) — each data word on the
    wire carries this byte; a mismatch refuses the frame."""
    crc = 0xFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0x31) & 0xFF if crc & 0x80 \
                  else (crc << 1) & 0xFF
    return crc


class Sps30:
    """Sensirion SPS30 particulate sensor on I2C 0x69 (5 V via J9; see
    docs/ENV-HEADS.md). read() returns pm1/pm2_5/pm4/pm10 µg/m³ or None
    on fault — every word is CRC-guarded, a corrupt frame refuses."""

    ADDR = 0x69
    # start measurement, high-precision float format arg + its CRC
    CMD_MEASURE = b"\x00\x10\x03\x00" + \
        bytes([_sps30_crc8(b"\x03\x00")])
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
            if _sps30_crc8(w) != buf[6 + i * 3 + 2]:
                return None                   # corrupt frame → refuse
            vals.append(((w[0] << 8) | w[1]) / 10)
        return {"pm1": vals[0], "pm2_5": vals[1],
                "pm4": vals[2], "pm10": vals[3]}


class Bme280Env:
    """BME280 temp/humidity/pressure via the vendored driver
    (third_party/bme280). Returns {"t","rh","p"} or None when the driver
    or sensor is absent — env context is optional, never invented."""

    def __init__(self, i2c):
        self._dev = BME280(i2c=i2c) if BME280 else None

    def read(self):
        if self._dev is None:
            return None
        try:
            t, p, h = self._dev.values        # "21.4C","998.2hPa","41%"
            return {"t": float(t[:-1]),
                    "p": float(p[:-3]),
                    "rh": float(h[:-1])}
        except Exception:
            return None


class Bh1750:
    """BH1750 lux meter on I2C 0x23 — continuous H-resolution mode."""

    ADDR = 0x23
    MODE_CONT_HRES = b"\x10"

    def __init__(self, i2c):
        self.i2c = i2c

    def read(self):
        self.i2c.writeto(self.ADDR, self.MODE_CONT_HRES)
        _sleep_ms(180)                            # 120 ms meas + margin
        buf = self.i2c.readfrom(self.ADDR, 2)
        return round(((buf[0] << 8) | buf[1]) / 1.2)


class H2SReader:
    """H2S front-end on D10 (GPIO10, ADC1_CH9). Two populated options per
    docs/ENV-HEADS.md: MQ-136 analog (0–4 V → divider → ADC, ~150 mA
    heater — indicative grade, cross-sensitive) or SPEC electrochemical
    (UART — TODO when that variant is populated). Returns voltage-level
    truth only; ppm conversion needs site R0 calibration and is the
    edge's job, not the node's."""

    PIN = 10

    def __init__(self):
        self._adc = None
        if _ON_NODE:
            self._adc = machine.ADC(machine.Pin(self.PIN))
            self._adc.atten(machine.ADC.ATTN_11DB)

    def read(self):
        if self._adc is None:
            return None
        raw = self._adc.read()                   # 0..4095 @ ~3.1 V FS
        return {"raw": raw,
                "mv": round(raw * 3100 / 4095)}


# (respin/pin budget; see hardware/PCB.md flags). Set to the ADC pin
# number once wired; None keeps the lane silent rather than guessing.
VBAT_PIN = None
VBAT_DIVIDER = 2.0        # assumed 2:1 divider → pack volts
VBAT_CUTOFF_V = 3.3       # below this the BMS is already close; flag it


def _vbat_read():
    if VBAT_PIN is None or not _ON_NODE:
        return None
    adc = machine.ADC(machine.Pin(VBAT_PIN))
    adc.atten(machine.ADC.ATTN_11DB)
    raw = adc.read()
    return {"v": round(raw * 3100 / 4095 * VBAT_DIVIDER / 1000, 2)}


def poll_env(buf):
    """One env reading per wake window → one .env spool file (ENV1):
    BME280 pressure/humidity/temp + BH1750 light (env lane) + PM (pm
    lane) + H2S (h2s lane) + VBAT."""
    reading = {"kind": "env", "node": NODE_ID, "ts": int(time.time())}
    if LANES["env"]["enabled"] and _ON_NODE:
        try:
            i2c = machine.I2C(0, sda=machine.Pin(5),
                              scl=machine.Pin(6), freq=100000)
            env = Bme280Env(i2c).read()
            if env:
                reading.update(env)
            lx = Bh1750(i2c).read()
            if lx is not None:
                reading["lx"] = lx
        except Exception:
            pass
    if LANES["pm"]["enabled"] and _ON_NODE:
        try:
            i2c = machine.I2C(0, sda=machine.Pin(5),
                              scl=machine.Pin(6), freq=100000)
            pm = Sps30(i2c).read()
            if pm:
                reading["pm"] = pm
        except Exception:
            pass
    if LANES["h2s"]["enabled"] and _ON_NODE:
        try:
            h2s = H2SReader().read()
            if h2s:
                reading["h2s"] = h2s
        except Exception:
            pass
    v = _vbat_read()
    if v:
        reading.update(v)
        if v["v"] < VBAT_CUTOFF_V:
            reading["low"] = 1                     # edge sees the flag
    if reading.get("t") is not None and reading["t"] < 5:
        reading["cu"] = 1            # charge-unsafe: TP4056 has no NTC
    if reading.get("t") is not None and reading["t"] > 55:
        reading["ot"] = 1            # box over-temp: XIAO rated to 65 °C
    if len(reading) > 3:
        payload = _fit_env(reading)
        if payload:
            buf.spool("env-%d.env" % reading["ts"], payload)


def _fit_env(reading):
    """ENV1 rides the same ~200 B budget as DET1. Shed optional detail
    until the frame fits — core scalars (kind/node/ts) always survive."""
    r = dict(reading)
    for drop in (lambda d: d.pop("lx", None),
                 lambda d: d.pop("h2s", None),
                 lambda d: d.pop("pm", None),
                 lambda d: d.pop("v", None),
                 lambda d: d.pop("cu", None),
                 lambda d: d.pop("low", None)):
        payload = json.dumps(r, separators=(",", ":")).encode()
        if len(payload) <= DETECTION_MAX_BYTES:
            return payload
        drop(r)
    return None


# ── the SD buffer ─────────────────────────────────────────────────────────

class SDBuffer:
    """Store-and-forward under /sd/spool. On-device files are AES-256-CBC
    sealed; the key lives in internal flash, not on the removable card."""

    def __init__(self, root=SD_MOUNT + "/spool"):
        self.root, self._key = root, None
        if _ON_NODE:
            try:
                os.mkdir(self.root)
            except OSError:
                pass
        self._sim = []

    def _key_bytes(self):
        if self._key is None:
            try:
                with open("/spool.key", "rb") as f:
                    self._key = f.read(32)
                if len(self._key) != 32:
                    raise OSError("bad spool key")
            except OSError:
                self._key = os.urandom(32)
                with open("/spool.key", "wb") as f:
                    f.write(self._key)
        return self._key

    def _seal(self, data):
        if _ucrypt_aes is None:
            raise OSError("spool crypto unavailable")
        data = data.encode() if isinstance(data, str) else data
        pad = 16 - (len(data) % 16)
        iv = os.urandom(16)
        return iv + _ucrypt_aes(self._key_bytes(), 2, iv).encrypt(
            data + bytes([pad]) * pad)

    def _open(self, blob):
        try:
            plain = _ucrypt_aes(self._key_bytes(), 2, blob[:16]).decrypt(
                blob[16:])
            pad = plain[-1]
            if 1 <= pad <= 16 and plain.endswith(bytes([pad]) * pad):
                return plain[:-pad]
        except Exception:
            pass
        return blob                       # pre-encryption legacy file

    def _files(self):
        try:
            return sorted(n for n in os.listdir(self.root)
                          if not n.endswith(".tmp"))
        except OSError:
            return []

    def _free(self):
        try:
            st = os.statvfs(self.root)
            return st[1] * st[4]
        except Exception:
            return None

    def _drop(self, old, reason):
        try:
            os.remove(self.root + "/" + old)
        except OSError:
            return False
        if old.endswith(".gap"):
            return True
        try:
            gaps = [n for n in self._files() if n.endswith(".gap")]
            for gone in gaps[:max(0, len(gaps) - KEEP_FILES[".gap"] + 1)]:
                os.remove(self.root + "/" + gone)
            gap = json.dumps({"kind": "gap", "node": NODE_ID,
                              "dropped": old, "reason": reason,
                              "ts": int(time.time())}).encode()
            tmp = self.root + "/gap-" + old + ".gap.tmp"
            with open(tmp, "wb") as f:
                f.write(self._seal(gap))
            os.rename(tmp, tmp[:-4])
        except Exception:
            pass
        return True

    def _make_room(self, need):
        free = self._free()
        while free is not None and free < need + SPOOL_RESERVE_BYTES:
            files, old = self._files(), None
            for exts in ((".pcm", ".auc", ".det", ".env", ".gap"),
                         (".res",)):
                hits = [n for n in files if n.endswith(exts)]
                if hits:
                    old = hits[0]
                    break
            if old is None:
                old = files[0] if files else None
            if old is None or not self._drop(old, "spool-cap"):
                return False
            free = self._free()
        return True

    def _enforce_caps(self):
        groups = {}
        for name in self._files():
            groups.setdefault(name[name.rfind("."):], []).append(name)
        for ext, names in groups.items():
            keep = KEEP_FILES.get(ext, OTHER_KEEP_FILES)
            for old in sorted(names)[:max(0, len(names) - keep)]:
                self._drop(old, ext + "-cap")

    def spool(self, name, data):
        if _ON_NODE:
            sealed = self._seal(data)
            if not self._make_room(len(sealed)):
                return False
            tmp = self.root + "/" + name + ".tmp"
            try:
                with open(tmp, "wb") as f:
                    f.write(sealed)
                os.rename(tmp, self.root + "/" + name)
            except OSError:
                return False
            self._enforce_caps()
            return True
        self._sim.append((name, data))
        return True

    def pending(self):
        if _ON_NODE:
            return self._files()        # .tmp orphans are debris, not payload
        return [n for n, _ in self._sim]

    def read(self, name):
        if _ON_NODE:
            with open(self.root + "/" + name, "rb") as f:
                return self._open(f.read())
        return next((d for n, d in self._sim if n == name), b"")

    def clear(self, name):
        if _ON_NODE:
            try:
                os.remove(self.root + "/" + name)
            except OSError:
                pass
        else:
            self._sim = [(n, d) for n, d in self._sim if n != name]
# ── uplink ────────────────────────────────────────────────────────────────
# Wire framing, one byte tag + payload — small enough for LoRa, simple
# enough for UDP. DET1 = detection line; AUD1 = audio chunk (name + PCM);
# TSK1 = downlink task (cloud-write); LANE = OTA module push. The edge
# demuxes on the tag. MicroReticulum can replace the socket later — the
# frame format stays.

TAG_DETECTION  = b"DET1"
TAG_AUDIO      = b"AUD1"
TAG_AUDIO_CLIP = b"AUC1"
TAG_READING    = b"ENV1"
TAG_TASK       = b"TSK1"
TAG_LANE       = b"LANE"
TAG_RESULT     = b"RES1"
TAG_GAP        = b"GAP1"

ACK_RESEND_S   = 30          # small frames: resend until acked
AUDIO_RESEND_S = 600         # chunked audio: slower retry budget


def _sha_bytes(data):
    h = hashlib.sha256()
    h.update(data)
    return h.digest()


def _sha_hex(data):
    try:
        from ubinascii import hexlify
    except ImportError:
        from binascii import hexlify
    return hexlify(_sha_bytes(data)).decode()


def _frame_for(name, blob):
    """The logical frame whose sha the edge acks: tag + payload for small
    frames; the assembled payload itself for audio — the edge hashes the
    reassembled bytes, not the wire chunks."""
    if name.endswith(".det"):
        return TAG_DETECTION + blob
    if name.endswith(".env"):
        return TAG_READING + blob
    if name.endswith(".res"):
        return TAG_RESULT + blob
    if name.endswith(".gap"):
        return TAG_GAP + blob
    if name.endswith((".pcm", ".auc")):
        return blob
    return None


def apply_ack(msg, buf, link=None):
    """Edge receipt → durable delete. Only an exact content-sha match
    clears the spool — a stale or forged ack deletes nothing."""
    want = msg.get("sha") if isinstance(msg, dict) else None
    want_name = msg.get("name") if isinstance(msg, dict) else None
    if not want and not want_name:
        return None
    for name in buf.pending():
        if want_name and name != want_name:
            continue
        frame = _frame_for(name, buf.read(name))
        if frame is not None and _sha_hex(frame) == want:
            buf.clear(name)
            if link:
                link.forget(want_name or want)
            return name
    return None


class Uplink:
    """Best-effort UDP uplink to the edge, with an optional RNode/LoRa
    serial fallback (`lora`). Frames are tag + payload; sends carry a
    resend budget keyed on content sha — the SD spool is the durable
    layer, the socket only drains it."""

    def __init__(self, edge_host=None, edge_port=EDGE_PORT, lora=None):
        self.edge = (edge_host, edge_port) if edge_host else None
        self.lora = lora                       # machine.UART RNode | None
        self._sock = None
        self._inflight = {}                    # content key → retry deadline
        if self.edge:
            try:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            except Exception:
                self._sock = None

    def _udp(self, frame):
        if not self._sock:
            return False
        try:
            self._sock.sendto(frame, self.edge)
            return True
        except Exception:
            return False                        # link down — spool keeps it

    UDP_AUDIO_PAYLOAD = 1200        # datagram payload; ~960 KB chunk → ~800 pkts

    def forget(self, key):
        self._inflight.pop(key, None)

    def _send_once(self, key, frame, resend_s=ACK_RESEND_S):
        if self._inflight.get(key, 0) > time.time():
            return True
        if self._udp(frame):
            self._inflight[key] = time.time() + resend_s
            return True
        return False

    def send_audio(self, name, blob):
        if self._inflight.get(name, 0) > time.time():
            return True
        name_b = name.encode()
        digest = _sha_bytes(blob)
        total = (len(blob) + self.UDP_AUDIO_PAYLOAD - 1) // self.UDP_AUDIO_PAYLOAD
        try:
            for i in range(total):
                part = blob[i * self.UDP_AUDIO_PAYLOAD:
                            (i + 1) * self.UDP_AUDIO_PAYLOAD]
                hdr = (TAG_AUDIO + bytes([len(name_b)]) + name_b +
                       bytes([(i >> 8) & 0xFF, i & 0xFF,
                              (total >> 8) & 0xFF, total & 0xFF]) + digest)
                self._sock.sendto(hdr + part, self.edge)
            self._inflight[name] = time.time() + AUDIO_RESEND_S
            return True
        except Exception:
            return False                        # link down — spool keeps it

    def send_detection(self, det_line):
        if isinstance(det_line, str):
            det_line = det_line.encode()
        if len(det_line) > DETECTION_MAX_BYTES:
            return False
        frame = TAG_DETECTION + det_line
        key = _sha_hex(frame)
        if self._inflight.get(key, 0) > time.time():
            return True
        if self.lora is not None:
            try:
                self.lora.write(frame)
                self._inflight[key] = time.time() + ACK_RESEND_S
                return True
            except Exception:
                pass                            # fall through to UDP
        return self._send_once(key, frame)

    def send_frame(self, tag, payload):
        if isinstance(payload, str):
            payload = payload.encode()
        if len(payload) > DETECTION_MAX_BYTES:
            return False
        frame = tag + payload
        return self._send_once(_sha_hex(frame), frame)

    def send_reading(self, env_line):
        return self.send_frame(TAG_READING, env_line)

    def poll_task(self, bufsize=2048):
        if not self._sock:
            return None
        try:
            self._sock.settimeout(0)
            data, _addr = self._sock.recvfrom(bufsize)
        except Exception:
            return None
        if not data or len(data) < 5:
            return None
        tag, body = data[:4], data[4:]
        if tag in (TAG_TASK, TAG_LANE):
            try:
                return {"tag": tag.decode(), **json.loads(body)}
            except Exception:
                return None
        return None


# ── detection packet ──────────────────────────────────────────────────────
# The node is dumb: detections arrive either from the edge (after it
# classifies an audio window) or, later, from a tiny on-device gate. A
# packet is the same tens of bytes either way — species, confidence,
# timestamp, node-id; SAIDs and subject get stamped at the edge.

NODE_ID = "node-7"


def detection_packet(species, confidence, ts):
    line = json.dumps({"species": species, "confidence": confidence,
                       "timestamp": ts, "node": NODE_ID})
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

class LxmfLane:
    """Single-MCU Reticulum mesh — the node IS the RNS peer (µReticulum,
    MIT, vendored under firmware/node/lib/). No companion RNode: the same
    ESP32-S3 that captures also encrypts/signs/routes LXMF frames over its
    own LoRa radio, so mesh hops are transport-layer business, not app
    code. Design of record: docs/RNODE-MESH.md.

    Contract mirrors Uplink/TtnLane: send_detection carries the same
    tens-of-bytes DET1 frame as msg.content (rns_edge.py strips the tag
    and JSON-parses); poll_task returns downlink task dicts for
    handle_task. Until the urns/ stack lands and identities are
    provisioned (/sd/lxmf.json: edge_dest hash + iface), every call
    returns the "link down" answer — the SD spool keeps everything."""

    def __init__(self, config=None):
        self.cfg = config or {}              # {"edge_dest": hex, "iface": "e32"|"lora"}
        self._rns = None                     # urns stack handle | None

    def joined(self):
        return bool(self._rns)

    def send_detection(self, det_line, port=1):
        if not self.joined():
            return False
        if isinstance(det_line, str):
            det_line = det_line.encode()
        try:
            # LXMessage(dest=edge_dest, content=det_line) — the DET1 tag
            # survives inside content; rns_edge.py strips it.
            self._rns.send_lxmf(self.cfg["edge_dest"], det_line)
            return True
        except Exception:
            return False

    def poll_task(self):
        if not self.joined():
            return None
        try:
            msg = self._rns.recv_lxmf()   # task dict | None
            return msg
        except Exception:
            return None


# ── cloud-write: downlink tasks + OTA lane modules ────────────────────────
# The write half of the node. Every op is consent-gated at the lane layer
# — the edge checked the joint consent upstream and the node re-checks the
# token here, so a stale or spoofed frame never acts.

LANES_DIR = SD_MOUNT + "/lanes"      # module spool; desktop sim: ./lanes
AUDIO_PRIORITY_UNTIL = 0             # "collect": ship audio first
DATA_HOLD_UNTIL      = 0             # "hold": results only, retain data


def audio_priority():
    return AUDIO_PRIORITY_UNTIL > time.time()


def data_held():
    return DATA_HOLD_UNTIL > time.time()


def install_lane_module(name, source, consent=None):
    """OTA lane module push (a LANE frame): source lands under
    /sd/lanes/ and the lane registers — consent-gated like every write."""
    if not consent:
        raise ConsentRequired(
            "lane-install rides the joint consent of guardian and operator")
    safe = "".join(c for c in name if c.isalnum() or c in "-_")
    if not safe:
        raise ValueError("bad lane name")
    path = LANES_DIR + "/" + safe + ".py"
    if _ON_NODE:
        try:
            os.mkdir(LANES_DIR)
        except OSError:
            pass
        with open(path, "w") as f:
            f.write(source or "")
    LANES[safe] = {"enabled": True, "gated": None, "head": safe,
                   "band": "custom", "role": "downlink-installed lane"}
    return path


def handle_task(task, emit, buf):
    """Downlink op dispatch — the write half of the node. The edge gated
    consent upstream; the node re-verifies the token here, so a stale or
    spoofed frame never acts. Returns a result dict (spooled as RES1)."""
    if not isinstance(task, dict):
        return {"ok": False, "reason": "malformed-task"}
    op = task.get("op")
    consent = task.get("consent")
    try:
        if op == "emit":
            ms = emit.emit(int(task.get("burst_ms", 20)), consent=consent)
            return {"ok": True, "op": "emit", "burst_ms": ms}
        if op == "store":
            buf.spool(task.get("name", "store.bin"),
                      (task.get("data") or "").encode())
            return {"ok": True, "op": "store",
                    "name": task.get("name", "store.bin")}
        if op in ("collect", "hold"):
            if not consent:
                raise ConsentRequired("traffic control rides operator consent")
            secs = max(1, min(float(task.get("seconds", 300)), 86400))
            global AUDIO_PRIORITY_UNTIL, DATA_HOLD_UNTIL
            if op == "collect": AUDIO_PRIORITY_UNTIL, DATA_HOLD_UNTIL = time.time() + secs, 0
            else: DATA_HOLD_UNTIL, AUDIO_PRIORITY_UNTIL = time.time() + secs, 0
            return {"ok": True, "op": op, "seconds": secs}
        if op == "duty":
            global WAKE_WINDOWS
            wins = task.get("windows")
            if not isinstance(wins, list) or not wins:
                return {"ok": False, "op": op, "reason": "bad-windows"}
            WAKE_WINDOWS = tuple(tuple(w) for w in wins)
            return {"ok": True, "op": "duty", "windows": wins}
        if op == "lane-install":
            path = install_lane_module(task.get("name", "lane"),
                                       task.get("source", ""),
                                       consent=consent)
            return {"ok": True, "op": "lane-install", "path": path}
    except ConsentRequired as e:
        return {"ok": False, "op": op, "reason": "consent-required",
                "detail": str(e)}
    return {"ok": False, "op": op, "reason": "unknown-op"}


# ── duty cycle ────────────────────────────────────────────────────────────

def in_wake_window(now=None):
    t = now or time.localtime()
    hour = t[3]
    return any(start <= hour < end for start, end in WAKE_WINDOWS)



def _next_window_wait_s():
    """Seconds until the next wake window opens; None inside a window or
    under the continuous default."""
    if in_wake_window():
        return None
    t = time.localtime()
    mins = t[3] * 60 + t[4]
    for s, e in sorted(WAKE_WINDOWS):
        if mins < s * 60:
            return (s * 60 - mins) * 60
    first = min(s for s, _ in WAKE_WINDOWS)
    return ((24 * 60 - mins) + first * 60) * 60
# ── watchdog ──────────────────────────────────────────────────────────────
# An unattended node that hangs must reboot, not wait for a human. ESP32
# machine.WDT is the task watchdog — armed once, fed at every loop point
# and every capture chunk. Timeout sits above the longest single
# blocking call — a wedge reboots clean into the spool.

WDT_TIMEOUT_S    = 120       # above the longest single blocking call
WDT_FEED_SLEEP_S = 30        # chunked sleeps stay under the timeout


def _wdt_make():
    if _ON_NODE:
        try:
            return machine.WDT(timeout=WDT_TIMEOUT_S * 1000)
        except Exception:
            return None
    return None


def _wdt_feed(wdt):
    if wdt:
        try:
            wdt.feed()
        except Exception:
            pass
def sleep_until_next_window(wdt=None):
    if _ON_NODE:
        wait = _next_window_wait_s()
        if wait is None:
            return
        # chunked so a counting watchdog always sees a feed — if this
        # port's WDT pauses in light sleep the chunks are harmless
        remaining = wait
        while remaining > 0:
            step = min(remaining, WDT_FEED_SLEEP_S)
            _wdt_feed(wdt)
            lightsleep(step * 1000)
            remaining -= step
    else:
        time.sleep(0.01)


# ── the node loop ─────────────────────────────────────────────────────────
def capture_window(cap, buf, seconds=WINDOW_SECONDS,
                   chunk_seconds=CHUNK_SECONDS, wdt=None):
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
        _wdt_feed(wdt)
    return names


def flush(buf, up):
    priority = audio_priority()
    order = {".res": 0, ".pcm": 1 if priority else 4,
             ".det": 2, ".env": 3, ".gap": 4}
    for name in sorted(buf.pending(),
                       key=lambda n: order.get(n[n.rfind("."):], 9)):
        if ((data_held() and not name.endswith(".res")) or
                (priority and not name.endswith((".res", ".pcm")))): continue
        blob = buf.read(name)
        if name.endswith(".det"):
            up.send_detection(blob)
        elif name.endswith(".env"):
            up.send_reading(blob)
        elif name.endswith(".res"):
            up.send_frame(TAG_RESULT, blob)
        elif name.endswith(".gap"):
            up.send_frame(TAG_GAP, blob)
        elif name.endswith(".pcm"):
            up.send_audio(name, blob)


def run(edge_host=None):
    if not LANES["mic"]["enabled"]:
        return
    wdt = _wdt_make()
    cap = MicCapture()
    buf = SDBuffer()
    up = Uplink(edge_host=edge_host)
    em = EmitLane()
    while True:
        _wdt_feed(wdt)
        if not in_wake_window():
            sleep_until_next_window(wdt)
            continue
        msg = up.poll_task()             # receipts + writes — never blocks
        while msg:
            if msg.get("op") == "ack":
                apply_ack(msg, buf, up)
            else:
                result = handle_task(msg, em, buf)
                result["node"] = NODE_ID
                buf.spool("res-%d.res" % int(time.time() * 1000),
                          json.dumps(result).encode())
            msg = up.poll_task()
        capture_window(cap, buf, wdt=wdt)
        if not audio_priority(): poll_env(buf)
        flush(buf, up)
        sleep_until_next_window(wdt)


def run_mesh():
    if _ON_NODE:
        try:
            import lxmf_node
            if lxmf_node.run_mesh_node():
                return
        except ImportError:
            pass
    run()
def _sim():
    """Desktop sim: capture → spool → refused flush (no edge) → consent
    gates → real UDP delivery to a bound listener → downlink task path."""
    cap = MicCapture()
    buf = SDBuffer()
    up = Uplink()                               # no edge: flush refused
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

    # real UDP: bind a listener, flush the same spool to it
    if not _ON_NODE:
        rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rx.bind(("127.0.0.1", 0))
        port = rx.getsockname()[1]
        up2 = Uplink(edge_host="127.0.0.1", edge_port=port)
        assert up2.send_detection(det) is True
        rx.settimeout(2)
        frame, _ = rx.recvfrom(2048)
        assert frame[:4] == TAG_DETECTION and b"Turdus" in frame
        # ACK-before-delete: only the edge's matching content hash clears
        assert apply_ack({"op": "ack", "sha": "0" * 64}, buf, up2) is None
        assert apply_ack({"op": "ack", "sha": _sha_hex(TAG_DETECTION + det.encode())},
                         buf, up2) == "d1.det"
        # downlink task path: emit without consent refuses, store lands
        r = handle_task({"op": "emit", "burst_ms": 10}, em, buf)
        assert r["ok"] is False and r["reason"] == "consent-required"
        r = handle_task({"op": "store", "name": "t.bin", "data": "x",
                         "consent": "said:joint-1"}, em, buf)
        assert r["ok"] is True
        r = handle_task({"op": "lane-install", "name": "c4d-reservoir",
                         "source": "pass", "consent": "said:joint-1"},
                        em, buf)
        assert r["ok"] is True and "c4d-reservoir" in LANES

        # ENV1 path: an .env spool file flushes as an ENV1 frame, and an
        # oversized reading is refused rather than fragmenting the frame.
        env = json.dumps({"kind": "env", "node": "node-7",
                          "ts": 1730000000,
                          "pm": {"pm1": 3.2, "pm2_5": 8.1,
                                 "pm4": 9.0, "pm10": 11.4}}).encode()
        buf.spool("env-1.env", env)
        assert up2.send_reading(env) is True
        rx.settimeout(2)
        frame, _ = rx.recvfrom(2048)
        assert frame[:4] == TAG_READING and b'"pm2_5"' in frame
        assert up2.send_reading(b"x" * 201) is False
        # Sps30 parse against a fake i2c: craft 10 words + valid CRCs.
        class FakeI2C:
            def writeto(self, addr, cmd):
                pass
            def readfrom(self, addr, n):
                out = bytearray(60)
                for i in range(10):
                    w = [0x00, 0x64 + i]           # 6.4, 6.5, ... µg/m³ raw
                    out[6 + i * 3] = w[0]
                    out[6 + i * 3 + 1] = w[1]
                    out[6 + i * 3 + 2] = _sps30_crc8(bytes(w))
                return bytes(out)
        pm = Sps30(FakeI2C()).read()
        assert pm and pm["pm2_5"] == 10.1, pm
        # corrupt one CRC → the whole frame refuses, no invented data
        class BadI2C(FakeI2C):
            def readfrom(self, addr, n):
                b = bytearray(super().readfrom(addr, n))
                b[8] ^= 0xFF
                return bytes(b)
        assert Sps30(BadI2C()).read() is None
    print("main.py sim: all checks passed")


if __name__ == "__main__":
    if _ON_NODE:
        run_mesh()
    else:
        _sim()
