# SPDX-License-Identifier: AGPL-3.0-or-later
# tools/edge/test_durable_ingest.py — durable receipt regression tests.

import hashlib
import importlib.util
import json
import os
import socket
import sys
import tempfile
import unittest

from durable_ingest import DurableIngest, TAGS, AUDIO_TAG, AUDIO_PAYLOAD

NODE_DIR = os.path.join(os.path.dirname(__file__), "..", "..",
                        "firmware", "node")
sys.path.insert(0, NODE_DIR)
import main as node                          # noqa: E402
_spec = importlib.util.spec_from_file_location(
    "node_adpcm", os.path.join(NODE_DIR, "adpcm.py"))
node_adpcm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(node_adpcm)


def audio_frame(name, blob, idx, total, payload):
    n = name.encode()
    return (AUDIO_TAG + bytes([len(n)]) + n +
            bytes([idx >> 8, idx & 255, total >> 8, total & 255]) +
            hashlib.sha256(blob).digest() + payload)


class DurableIngestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.tmp.name, "store")
        self.ledger = os.path.join(self.tmp.name, "ledger.jsonl")
        self.ingest = DurableIngest(self.root, self.ledger)

    def tearDown(self):
        self.ingest.ledger.close()
        self.tmp.cleanup()

    def test_record_commit_ack_duplicate_and_restart(self):
        frame = b'DET1{"node":"n1","species":"x","confidence":0.5,"timestamp":1}'
        ack = self.ingest.commit_record(frame, "test")
        self.assertEqual(ack["sha"], hashlib.sha256(frame).hexdigest())
        dup = self.ingest.commit_record(frame, "test")
        self.assertTrue(dup["dup"])
        self.ingest.ledger.close()
        again = DurableIngest(self.root, self.ledger)
        self.assertTrue(again.commit_record(frame, "test")["dup"])
        again.ledger.close()
        self.ingest.ledger = open(self.ledger, "a")
        with open(self.ledger) as fh:
            self.assertEqual(len(fh.readlines()), 1)

    def test_record_rejects_corrupt_json(self):
        self.assertIsNone(self.ingest.commit_record(b"DET1{bad", "test"))
        self.assertIsNone(self.ingest.commit_record(b"ENV1{}", "test"))

    def test_audio_reassembly_ack_and_lost_ack_retry(self):
        blob = bytes(range(256)) * 10
        total = (len(blob) + AUDIO_PAYLOAD - 1) // AUDIO_PAYLOAD
        frames = [audio_frame("w1.pcm", blob, i, total,
                              blob[i * AUDIO_PAYLOAD:(i + 1) * AUDIO_PAYLOAD])
                  for i in range(total)]
        self.assertIsNone(self.ingest.receive_audio(frames[1], "udp"))
        self.assertIsNone(self.ingest.receive_audio(frames[0], "udp"))
        self.assertIsNone(self.ingest.receive_audio(frames[0], "udp"))
        ack = self.ingest.receive_audio(frames[2], "udp")
        self.assertEqual(ack["sha"], hashlib.sha256(blob).hexdigest())
        # Lost ACK → any retransmitted chunk gets the same content ACK.
        self.assertEqual(self.ingest.receive_audio(frames[0], "udp")["sha"],
                         ack["sha"])
        self.assertTrue(os.path.exists(
            os.path.join(self.root, "committed", ack["sha"] + ".pcm")))

    def test_corrupt_audio_is_not_committed(self):
        blob = b"a" * (AUDIO_PAYLOAD + 3)
        good = audio_frame("w2.pcm", blob, 1, 2, blob[AUDIO_PAYLOAD:])
        bad_first = audio_frame("w2.pcm", blob, 0, 2, b"b" * AUDIO_PAYLOAD)
        self.assertIsNone(self.ingest.receive_audio(good, "udp"))
        self.assertIsNone(self.ingest.receive_audio(bad_first, "udp"))
        self.assertFalse(os.listdir(
            os.path.join(self.root, "committed")))

    def test_auc_clip_roundtrip_and_ack(self):
        pcm = bytes(range(256)) * 40
        payload = node_adpcm.clip_packet(pcm, "n1", "w1.pcm")
        frame = node.TAG_AUDIO_CLIP + payload
        ack = self.ingest.commit_record(frame, "mesh-test")
        self.assertEqual(ack["kind"], "audio-clip")
        self.assertTrue(os.path.exists(
            os.path.join(self.root, "committed", ack["sha"] + ".wav")))
        buf = node.SDBuffer()
        buf.spool("w1.auc", payload)
        self.assertEqual(node.apply_ack(ack, buf), "w1.auc")

    def test_firmware_audio_wire_format(self):
        rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rx.bind(("127.0.0.1", 0))
        rx.settimeout(2)
        up = node.Uplink("127.0.0.1", rx.getsockname()[1])
        blob = bytes(range(256)) * 10
        self.assertTrue(up.send_audio("w-node.pcm", blob))
        ack = None
        while ack is None:
            frame, _ = rx.recvfrom(65535)
            ack = self.ingest.handle_frame(frame, "udp-test")
        rx.close()
        up._sock.close()
        self.assertEqual(ack["sha"], hashlib.sha256(blob).hexdigest())
        buf = node.SDBuffer()
        buf.spool("w-node.pcm", blob)
        self.assertEqual(node.apply_ack(ack, buf, up), "w-node.pcm")
        self.assertEqual(buf.pending(), [])

    def test_audio_partial_state_survives_edge_restart(self):
        blob = b"z" * (AUDIO_PAYLOAD * 2 + 17)
        frames = [audio_frame("restart.pcm", blob, i, 3,
                              blob[i * AUDIO_PAYLOAD:(i + 1) * AUDIO_PAYLOAD])
                  for i in range(3)]
        self.assertIsNone(self.ingest.receive_audio(frames[0], "udp"))
        self.assertIsNone(self.ingest.receive_audio(frames[1], "udp"))
        self.ingest.ledger.close()
        again = DurableIngest(self.root, self.ledger)
        ack = again.receive_audio(frames[2], "udp")
        again.ledger.close()
        self.ingest.ledger = open(self.ledger, "a")
        self.assertEqual(ack["sha"], hashlib.sha256(blob).hexdigest())
        self.assertTrue(os.path.exists(
            os.path.join(self.root, "committed", ack["sha"] + ".pcm")))

    def test_node_restart_pending_and_encrypted_spool_migration(self):
        class FakeCipher:
            def __init__(self, key, mode, iv):
                self.key = key + iv
            def _xor(self, data):
                return bytes(b ^ self.key[i % len(self.key)]
                             for i, b in enumerate(data))
            def encrypt(self, data):
                return self._xor(data)
            def decrypt(self, data):
                return self._xor(data)

        old_on_node, old_aes = node._ON_NODE, node._ucrypt_aes
        node._ON_NODE = True
        node._ucrypt_aes = lambda key, mode, iv: FakeCipher(key, mode, iv)
        root = os.path.join(self.tmp.name, "node-spool")
        try:
            first = node.SDBuffer(root)
            first._key_bytes = lambda: b"k" * 32
            det = b'{"node":"n1","species":"x","confidence":0.5,"timestamp":1}'
            env = b'{"node":"n1","kind":"env","t":1}'
            pcm = b"p" * 64
            first.spool("d.det", det)
            first.spool("e.env", env)
            first.spool("w.pcm", pcm)
            with open(os.path.join(root, "d.det"), "rb") as fh:
                self.assertNotEqual(fh.read(), det)       # sealed at rest
            with open(os.path.join(root, "legacy.env"), "wb") as fh:
                fh.write(b'{"node":"n"}')                  # pre-crypto file

            again = node.SDBuffer(root)
            again._key_bytes = lambda: b"k" * 32
            self.assertEqual(again.pending(),
                             ["d.det", "e.env", "legacy.env", "w.pcm"])
            self.assertEqual(again.read("d.det"), det)
            self.assertEqual(again.read("legacy.env"), b'{"node":"n"}')
            self.assertEqual(node.apply_ack(
                {"op": "ack",
                 "sha": node._sha_hex(node.TAG_DETECTION + det)}, again),
                "d.det")
            self.assertEqual(node.apply_ack(
                {"op": "ack",
                 "sha": node._sha_hex(node.TAG_READING + env)}, again),
                "e.env")
            self.assertEqual(node.apply_ack(
                {"op": "ack", "name": "w.pcm",
                 "sha": node._sha_hex(pcm)}, again), "w.pcm")
            self.assertEqual(again.pending(), ["legacy.env"])
        finally:
            node._ON_NODE, node._ucrypt_aes = old_on_node, old_aes


if __name__ == "__main__":
    unittest.main()
