# SPDX-License-Identifier: AGPL-3.0-or-later
# firmware/node/lxmf_node.py — mesh-capable node loop (single MCU).
#
# WHAT THIS IS. The Reticulum half of the node, running IN-PROCESS on the
# same ESP32-S3 as main.py's capture/spool code — no companion RNode.
# It vendors µReticulum (MIT, varna9000/micropython-reticulum — see
# urns/, *.mpy, lora_boards.py beside this file) and drives it the way
# upstream's example_sensor.py does: Reticulum + LXMRouter inside
# uasyncio, LXMF delivery callbacks feeding our task queue, sends as
# async tasks because signing costs ~seconds of CPU.
#
# Design of record: docs/RNODE-MESH.md. Wire contract:
# tools/edge/rns_edge.py packet_to_detection() — LXMF content = the same
# DET1/ENV1 frame bytes UDP carries; tag stripped, JSON parsed, "node"
# required.
#
# PROVISIONING. No config file required — this module builds the
# interface config in code (E32 on D6/D7 UART) and reads node settings
# from /sd/lxmf.json:
#   {"edge_dest": "<64-hex LXMF destination hash>", "node_name": "...",
#    "transport": false, "wake_windows": [[4,10],[17,21]]}
# The RNS identity persists at /sd/rns/identity across flashes.

import json
import os
import time

try:
    import uasyncio as asyncio
    _ASYNC = True
except ImportError:
    asyncio = None
    _ASYNC = False                     # desktop sim / CPython

try:
    import machine
    _ON_NODE = True
except ImportError:
    machine = None
    _ON_NODE = False

try:
    from urns import Reticulum
    from urns.lxmf import LXMRouter
    _URNS = True
except ImportError:
    _URNS = False                      # stack not deployed beside us

try:
    from adpcm import clip_packet
except ImportError:
    clip_packet = None

from main import (SDBuffer, MicCapture, NODE_ID,
                  TAG_DETECTION, TAG_READING, TAG_RESULT, TAG_GAP,
                  TAG_AUDIO_CLIP, WAKE_WINDOWS, in_wake_window,
                  handle_task, EmitLane,
                  poll_env, apply_ack, _sha_hex, ACK_RESEND_S,
                  _wdt_make, _wdt_feed, sleep_until_next_window,
                  audio_priority, data_held, CHUNK_SECONDS,
                  WINDOW_SECONDS, SAMPLE_RATE, BITS)

SD = "/sd"; LXMF_CFG = SD + "/lxmf.json"; RNS_DIR = SD + "/rns"
AUC_DIVIDER = 2; _auc_phase = 0    # one low-rate clip / two PCM chunks

# E32-900T20D on the free UART — D6=GPIO43 (MCU TX), D7=GPIO44 (MCU RX).
# E32 TXD→GPIO44, RXD→GPIO43, GND common. M0/M1 strapped for transparent
# mode 0 on the module (or jumpered to D8/D9 if populated); AUX optional —
# the driver falls back to blind timing. 915 MHz ISM: channel = freq-862,
# ch 50 ≈ 912 MHz center. air_rate 2 = 2400 bps (max range).
E32_UART_ID = 1; E32_TX_PIN = 43; E32_RX_PIN = 44


def load_lxmf_config():
    """Node-side settings. Missing file → defaults; missing edge_dest →
    the node still joins the mesh and announces (useful for site surveys)
    but cannot deliver detections until provisioned."""
    cfg = {"edge_dest": None, "node_name": NODE_ID, "transport": False,
           "wake_windows": [list(w) for w in WAKE_WINDOWS]}
    try:
        with open(LXMF_CFG) as f:
            cfg.update(json.loads(f.read()))
    except Exception:
        pass
    if isinstance(cfg.get("wake_windows"), list):
        cfg["wake_windows"] = [tuple(w) for w in cfg["wake_windows"]]
    return cfg


def build_rns_config(transport=False):
    """The interface table Reticulum.setup_interfaces() consumes.
    WiFi UDP is deliberately absent — the playa has no infrastructure;
    add a UDPInterface entry here for campus cells that do."""
    return {
        "loglevel": 3,
        "enable_transport": bool(transport),
        "time_sync": {"enabled": True, "trusted_nodes": [],
                      "min_sources": 2, "tolerance": 120},
        "interfaces": [
            {"type": "E32Interface", "name": "LoRa E32",
             "enabled": True, "uart_id": E32_UART_ID,
             "tx_pin": E32_TX_PIN, "rx_pin": E32_RX_PIN,
             "speed": 9600,
             "channel": 50, "air_rate": 2, "tx_power": 0,
             "auto_configure": True},
        ],
    }


class MeshLink:
    """Reticulum+LXMF in-process. Mirrors the Uplink/TtnLane contract so
    flush()/handle_task() don't know which carrier carried the bytes:
    send_frame() for detections/env, recv_tasks() for downlinks."""

    def __init__(self, cfg):
        self.cfg, self.rns, self.router, self.dest = cfg, None, None, None
        self._tasks = self._send_q = None
        self._inflight = {}                     # content hash → retry deadline

    def setup(self):
        if not (_URNS and _ASYNC and _ON_NODE):
            return False
        try:
            os.makedirs(RNS_DIR, exist_ok=True)
        except OSError:
            pass
        self._tasks = asyncio.Queue()
        self._send_q = asyncio.Queue()
        self.rns = Reticulum(config_path=RNS_DIR + "/config.json")
        self.rns.config = build_rns_config(self.cfg.get("transport"))
        self.router = LXMRouter(identity=self.rns.identity)
        self.dest = self.router.register_delivery_identity(
            self.rns.identity,
            display_name=self.cfg["node_name"])

        def on_message(message):
            # LXMF delivery proof is automatic. Content is either a
            # downlink task JSON (has "op") or a peer frame we don't
            # originate — tasks queue for handle_task; anything else is
            # dropped here, receipted upstream if it matters.
            try:
                content = message.content
                if isinstance(content, bytes):
                    content = content.decode()
                    content = content.decode()
                task = json.loads(content)
                if isinstance(task, dict) and "op" in task:
                    self._tasks.put_nowait(task)   # task or edge ACK
            except Exception:
        return True

    async def _sender(self):
        """Serialized LXMF sends — signing is ~seconds of CPU; queue it
        so capture and the poll loop never block on crypto."""
        edge = (bytes.fromhex(self.cfg["edge_dest"])
                if self.cfg.get("edge_dest") else None)
        while True:
            content = await self._send_q.get()
            if edge is None:
                continue                    # unprovisioned: spool keeps it
            try:
                await asyncio.sleep(0)
                self.router.send_message(edge, content)
            except Exception:
                pass

    def forget(self, key):
        self._inflight.pop(key, None)

    def send_frame(self, frame):
        if self.router is None or not self.cfg.get("edge_dest"):
            return False
        key = _sha_hex(frame)
        if self._inflight.get(key, 0) > time.time():
            return True
        try:
            self._send_q.put_nowait(frame)
            self._inflight[key] = time.time() + ACK_RESEND_S
            return True
        except Exception:
            return False

    async def recv_tasks(self):
        try:
            return self._tasks.get_nowait()
        except asyncio.QueueEmpty:
            return None

    async def run(self, cap, buf, emit):
        """The node loop: wake windows → chunked capture (yielding to the
        RNS poll between chunks — a blocking 300 s capture would deafen
        the radio) → env poll → flush. Downlink tasks preempt each
        window."""
        # rns.run() is the packet pump: Transport.job_loop + each
        # interface's poll_loop live there. Without it announces queue
        # but never transmit and incoming LXMF is never processed.
        rns_runner = asyncio.create_task(self.rns.run())
        sender = asyncio.create_task(self._sender())
        announcer = asyncio.create_task(self._announcer())
        wdt = _wdt_make()
        try:
            while True:
                _wdt_feed(wdt)
                if not in_wake_window():
                    # duty-cycle the mesh too — lightsleep chunks keep
                    # RAM (RNS state survives) while the CPU drops to
                    # ~mA. Leaf nodes miss inbound traffic while asleep;
                    # that's the store-and-forward trade. transport=true
                    # relay nodes must stay awake instead — documented.
                    sleep_until_next_window(wdt)
                    await asyncio.sleep(0)      # let rns_runner resume
                    continue
                task = await self.recv_tasks()
                while task:
                    if task.get("op") == "ack":
                        apply_ack(task, buf, self)
                    else:
                        result = handle_task(task, emit, buf)
                        result["node"] = NODE_ID
                        buf.spool("res-%d.res" % int(time.time() * 1000),
                                  json.dumps(result).encode())
                    task = await self.recv_tasks()
                await capture_window_async(cap, buf, wdt=wdt)
                if not audio_priority(): poll_env(buf)
                await flush_mesh(buf, self)
                await asyncio.sleep(60)
        finally:
            sender.cancel()
            announcer.cancel()
            rns_runner.cancel()
            try:
                self.rns.shutdown()
            except Exception:
                pass

    async def _announcer(self):
        await asyncio.sleep(1)
        while True:
            try:
                self.router.announce()
            except Exception:
                pass
            await asyncio.sleep(120)


async def capture_window_async(cap, buf, seconds=WINDOW_SECONDS, wdt=None):
    global _auc_phase
    chunk_bytes = SAMPLE_RATE * BITS // 8 * CHUNK_SECONDS
    elapsed = 0
    while elapsed < seconds:
        pcm = cap.read(chunk_bytes)
        if not pcm:
            pcm = bytes(chunk_bytes)
        name = "w%d.pcm" % (int(time.time() * 1000) + elapsed)
        buf.spool(name, pcm)
        divider = 1 if audio_priority() else AUC_DIVIDER
        _auc_phase = (_auc_phase + 1) % divider
        if clip_packet and _auc_phase == 0:
            clip = clip_packet(pcm, NODE_ID, name)
            if clip:
                buf.spool(name[:-4] + ".auc", clip)
        elapsed += CHUNK_SECONDS
        _wdt_feed(wdt)
        await asyncio.sleep(0)


async def flush_mesh(buf, link):
    """Transmit priority records over LXMF and keep each file until the
    edge ACKs its content hash. .pcm stays for WiFi; .auc clips ride the
    same receipt path."""
    priority = audio_priority()
    order = {".res": 0, ".auc": 1 if priority else 4,
             ".det": 2, ".env": 3, ".gap": 4}
    for name in sorted(buf.pending(),
                       key=lambda n: order.get(n[n.rfind("."):], 9)):
        if (name.endswith(".pcm") or
                (data_held() and not name.endswith(".res")) or
                (priority and not name.endswith((".res", ".auc")))): continue
        blob = buf.read(name)
        if isinstance(blob, str):
            blob = blob.encode()
        if name.endswith(".det"):
            frame = TAG_DETECTION + blob
        elif name.endswith(".env"):
            frame = TAG_READING + blob
        elif name.endswith(".res"):
            frame = TAG_RESULT + blob
        elif name.endswith(".gap"):
            frame = TAG_GAP + blob
        elif name.endswith(".auc"):
            frame = TAG_AUDIO_CLIP + blob
        else:
            continue
        link.send_frame(frame)


def run_mesh_node():
    """Entry point for mesh builds: call instead of main.run() when
    µReticulum is deployed. Legacy UDP path stays for WiFi cells."""
    cfg = load_lxmf_config()
    if cfg.get("wake_windows"):
        import main as _main
        _main.WAKE_WINDOWS = tuple(cfg["wake_windows"])
    link = MeshLink(cfg)
    if not link.setup():
        return False
    cap = MicCapture()
    buf = SDBuffer()
    em = EmitLane()
    asyncio.run(link.run(cap, buf, em))
    return True
    asyncio.run(link.run(cap, buf, em))
    return True
    cap = MicCapture()
    buf = SDBuffer()
    em = EmitLane()
    asyncio.run(link.run(cap, buf, em))
    return True
