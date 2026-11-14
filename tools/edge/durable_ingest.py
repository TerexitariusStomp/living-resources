# SPDX-License-Identifier: AGPL-3.0-or-later
# tools/edge/durable_ingest.py — idempotent, crash-safe edge ingest.
#
# The node deletes an item only after this module has (a) received all
# bytes, (b) verified the content hash, and (c) fsynced the committed
# record. Duplicate sends are harmless: the content ID is the dedupe key.

import hashlib
import json
import os
import time

from adpcm import decode_clip, write_wav

TAGS = {b"DET1": "detection", b"ENV1": "env",
        b"RES1": "task-result", b"GAP1": "gap"}
AUDIO_TAG = b"AUD1"
AUDIO_CLIP_TAG = b"AUC1"
AUDIO_PAYLOAD = 1200


def sha_hex(data):
    return hashlib.sha256(data).hexdigest()


def _fsync(fh):
    fh.flush()
    os.fsync(fh.fileno())


def _safe(name):
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in name)


def parse_frame(frame):
    """Legacy small frame → (kind, record). RES1/GAP1 are acknowledged
    operational records, not detections."""
    if not isinstance(frame, bytes) or frame[:4] not in TAGS:
        return None
    try:
        rec = json.loads(frame[4:].decode())
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(rec, dict) or "node" not in rec:
        return None
    rec.setdefault("kind", TAGS[frame[:4]])
    return TAGS[frame[:4]], rec


def frame_node(frame):
    """Small/AUC1 frame → sender node id where the payload carries one."""
    parsed = parse_frame(frame)
    if parsed:
        return parsed[1].get("node")
    if isinstance(frame, bytes) and frame.startswith(AUDIO_CLIP_TAG):
        parsed = decode_clip(frame[len(AUDIO_CLIP_TAG):])
        return parsed[0].get("node") if parsed else None
    return None


def parse_audio_part(frame):
    """AUD1 | name-len | name | idx u16 | total u16 | sha256 | payload."""
    if not isinstance(frame, bytes) or not frame.startswith(AUDIO_TAG):
        return None
    if len(frame) < 42:
        return None
    nlen = frame[4]
    end = 5 + nlen + 4 + 32
    if len(frame) < end:
        return None
    name = frame[5:5 + nlen].decode("utf-8", "replace")
    idx = (frame[5 + nlen] << 8) | frame[6 + nlen]
    total = (frame[7 + nlen] << 8) | frame[8 + nlen]
    want = frame[9 + nlen:end].hex()
    if not name or not total or idx >= total or total > 65535:
        return None
    return {"name": name, "idx": idx, "total": total, "sha": want,
            "payload": frame[end:]}


class DurableIngest:
    """Content-addressed commit + ACK state for UDP/RNS edges.

    Layout:
      root/receipts.jsonl       one fsynced content ID per committed item
      root/incoming/            reassembly metadata + .part files
      root/committed/           complete payloads by content hash

    A caller must send the returned ACK only after receive_* returns it —
    that is the durable-receipt boundary.
    """

    def __init__(self, root, ledger_path, via=None):
        self.root = root
        self.ledger_path = ledger_path
        self.via = via
        self.receipts = os.path.join(root, "receipts.jsonl")
        self.names = os.path.join(root, "audio_names.json")
        self.incoming = os.path.join(root, "incoming")
        self.committed = os.path.join(root, "committed")
        for d in (root, self.incoming, self.committed):
            os.makedirs(d, exist_ok=True)
        self.seen = set()
        if os.path.exists(self.receipts):
            with open(self.receipts, "r") as fh:
                for line in fh:
                    try:
                        self.seen.add(json.loads(line)["sha"])
                    except Exception:
                        continue
        self.audio_names = {}
        if os.path.exists(self.names):
            try:
                with open(self.names) as fh:
                    self.audio_names = json.load(fh)
            except Exception:
                self.audio_names = {}
        self.ledger = open(ledger_path, "a")

    def _receipt(self, item_id):
        """The durable-receipt boundary: fsynced content ID, then in-memory
        seen — never the other way around."""
        self.seen.add(item_id)
        with open(self.receipts, "a") as fh:
            fh.write(json.dumps({"sha": item_id}) + "\n")
            _fsync(fh)

    def _ledger(self, rec):
        if self.via and "via" not in rec:
            rec["via"] = self.via
        self.ledger.write(json.dumps(rec, separators=(",", ":")) + "\n")
        _fsync(self.ledger)

    def _commit_blob(self, ext, blob, item_id):
        path = os.path.join(self.committed, item_id + ext)
        if not os.path.exists(path):
            tmp = path + ".tmp"
            with open(tmp, "wb") as fh:
                fh.write(blob)
                _fsync(fh)
            os.replace(tmp, path)
        return path

    def _remember_audio(self, name, item_id):
        self.audio_names[name] = item_id
        tmp = self.names + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(self.audio_names, fh)
            _fsync(fh)
        os.replace(tmp, self.names)

    def commit_clip(self, frame, source):
        """AUC1 clip (ADPCM-packed node audio) → committed payload + WAV
        sidecar; ack carries the payload hash the node can verify."""
        payload = frame[len(AUDIO_CLIP_TAG):]
        item_id = sha_hex(payload)
        if item_id in self.seen:
            return {"op": "ack", "sha": item_id, "dup": True}
        parsed = decode_clip(payload)
        if not parsed:
            return None
        meta, pcm = parsed
        payload = frame[len(AUDIO_CLIP_TAG):]
        item_id = sha_hex(payload)
        if item_id in self.seen:
            return {"op": "ack", "sha": item_id, "dup": True}
        parsed = decode_clip(payload)
        if not parsed:
            return None
        meta, pcm = parsed
        if "node" not in meta:
            return None
        auc_path = self._commit_blob(
            ".auc", frame[len(AUDIO_CLIP_TAG):], item_id)
        wav_path = os.path.splitext(auc_path)[0] + ".wav"
        tmp = wav_path + ".tmp"
        write_wav(tmp, meta, pcm)
        os.replace(tmp, wav_path)
        rec = dict(meta)
        rec.update({"kind": "audio-clip", "item_id": item_id,
                    "source": source, "edge_ts": time.time()})
        self._ledger(rec)
        self._receipt(item_id)
        return {"op": "ack", "sha": item_id, "kind": "audio-clip"}

    def commit_record(self, frame, source):
        """Small tagged record/AUC1 → ACK only after durable commit."""
        if frame.startswith(AUDIO_CLIP_TAG):
            return self.commit_clip(frame, source)
        item_id = sha_hex(frame)
        if item_id in self.seen:
            return {"op": "ack", "sha": item_id, "dup": True}
        parsed = parse_frame(frame)
        if parsed is None:
            return None
        kind, rec = parsed
        rec.update({"item_id": item_id, "source": source,
                    "edge_ts": time.time()})
        self._ledger(rec)
        self._receipt(item_id)
        return {"op": "ack", "sha": item_id, "kind": kind}

    def receive_audio(self, frame, source):
        """One AUD1 datagram → ACK dict once every chunk is durable and
        the reassembled PCM hash is committed. Partial state survives an
        edge restart; duplicate chunks are ignored by index."""
        part = parse_audio_part(frame)
        if part is None:
            return None
        old = self.audio_names.get(part["name"])
        if old:
            return {"op": "ack", "name": part["name"], "sha": old,
                    "kind": "audio", "dup": True}
        key = _safe(part["name"])
        meta_p = os.path.join(self.incoming, key + ".json")
        part_p = os.path.join(self.incoming, key + ".part")
        try:
            with open(meta_p) as fh:
                meta = json.load(fh)
        except Exception:
            meta = {"name": part["name"], "total": part["total"],
                    "sha": part["sha"], "have": [], "last": 0}
        if (meta.get("total") != part["total"] or
                meta.get("sha") != part["sha"]):
            return None
        if part["idx"] not in meta["have"]:
            mode = "r+b" if os.path.exists(part_p) else "w+b"
            with open(part_p, mode) as fh:
                fh.seek(part["idx"] * AUDIO_PAYLOAD)
                fh.write(part["payload"])
                _fsync(fh)
            meta["have"].append(part["idx"])
            if part["idx"] == part["total"] - 1:
                meta["last"] = len(part["payload"])
            tmp = meta_p + ".tmp"
            with open(tmp, "w") as fh:
                json.dump(meta, fh)
                _fsync(fh)
            os.replace(tmp, meta_p)
        if len(meta["have"]) != meta["total"]:
            return None
        size = (meta["total"] - 1) * AUDIO_PAYLOAD + meta["last"]
        with open(part_p, "rb") as fh:
            blob = fh.read(size)
        item_id = sha_hex(blob)
        if item_id != meta["sha"]:
            for p in (meta_p, part_p):
                try:
                    os.remove(p)
                except OSError:
                    pass
            return None                      # corrupt assembly: retry whole item
        out_p = os.path.join(self.committed, item_id + ".pcm")
        if not os.path.exists(out_p):
            tmp = out_p + ".tmp"
            with open(tmp, "wb") as fh:
                fh.write(blob)
                _fsync(fh)
            os.replace(tmp, out_p)
        self._remember_audio(part["name"], item_id)
        self._ledger({"kind": "audio", "name": part["name"],
                      "item_id": item_id, "size": size,
                      "source": source, "edge_ts": time.time()})
        self._receipt(item_id)
        for p in (meta_p, part_p):
            try:
                os.remove(p)
            except OSError:
                pass
        return {"op": "ack", "name": part["name"], "sha": item_id,
                "kind": "audio"}

    def handle_frame(self, frame, source):
        if frame.startswith(AUDIO_TAG):
            return self.receive_audio(frame, source)
        return self.commit_record(frame, source)
