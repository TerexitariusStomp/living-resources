# SPDX-License-Identifier: AGPL-3.0-or-later
# tools/edge/task_queue.py — append-only central downlink task queue.

import hashlib
import json
import os
import time

TASK_TAG = b"TSK1"
NAMED_RETRY_S = 10
NAMED_TTL_S = 300
BROADCAST_TTL_S = 60


def poll_task_file(path, offsets, queue):
    """Append-only JSONL: {"node":"node-7|*","task":{"op":...}}.
    Each queued item carries delivery state; file offset survives truncation."""
    if not path or not os.path.exists(path):
        return
    try:
        size = os.path.getsize(path)
        at = offsets.get(path, 0)
        if size < at:
            at = 0
        with open(path) as fh:
            fh.seek(at)
            while True:
                pos, line = fh.tell(), fh.readline()
                if not line:
                    break
                try:
                    rec = json.loads(line)
                    node, task = rec["node"], rec["task"]
                    if not (isinstance(task, dict) and "op" in task):
                        continue
                    ident = hashlib.sha256(
                        ("%s:%d:" % (path, pos)).encode() + line.encode()
                    ).hexdigest()
                    queue.setdefault(node, []).append(
                        {"id": ident, "task": task, "sent_at": 0,
                         "sent": set(),
                         "deadline": time.time() + float(
                             task.get("ttl", NAMED_TTL_S))})
                except Exception:
                    pass
            offsets[path] = fh.tell()
    except OSError:
        return


def acknowledge(queue, node, op):
    """A node RES1 result retires matching named tasks (idempotent)."""
    items = queue.get(node)
    if not items:
        return
    queue[node] = [item for item in items if item["task"].get("op") != op]
    if not queue[node]:
        queue.pop(node, None)


def pump_tasks(queue, destinations, send):
    """Try queued deliveries. Named tasks retry until acknowledge() or TTL;
    '*' tasks deliver once per known node and remain for their task TTL so
    late-contacting nodes also receive the hold/collect order."""
    now = time.time()
    for key, items in list(queue.items()):
        remaining = []
        for item in items:
            if key == "*":
                for node, dest in destinations.items():
                    if node not in item["sent"]:
                        try:
                            send(dest, item["task"])
                            item["sent"].add(node)
                        except Exception:
                            pass
                ttl = float(item["task"].get(
                    "ttl", item["task"].get("seconds", BROADCAST_TTL_S)))
                if now < item["deadline"] - NAMED_TTL_S + ttl:
                    remaining.append(item)
            else:
                dest = destinations.get(key)
                if dest is not None and now - item["sent_at"] >= NAMED_RETRY_S:
                    try:
                        send(dest, item["task"])
                        item["sent_at"] = now
                    except Exception:
                        pass
                if now < item["deadline"]:
                    remaining.append(item)
        if remaining:
            queue[key] = remaining
        else:
            queue.pop(key, None)
