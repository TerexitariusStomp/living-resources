# SPDX-License-Identifier: AGPL-3.0-or-later
# tools/edge/udp_edge.py — central WiFi ingest/task server for EcoCell nodes.
#
# Receives DET1/ENV1/RES1/GAP1 and chunked AUD1 frames, commits only
# hash-verified complete records, then returns TSK1 {"op":"ack",...}.
# That application ACK—not UDP send()—is what authorizes node deletion.
#
# Optional --tasks JSONL queues downlinks:
#   {"node":"node-7","task":{"op":"collect","seconds":900,"consent":"said:op"}}
#   {"node":"*","task":{"op":"hold","seconds":900,"consent":"said:op"}}

import argparse
import json
import socket
import sys
import time

from durable_ingest import DurableIngest, frame_node
from task_queue import TASK_TAG, poll_task_file, node_task_dests


def send_task(sock, addr, task):
    sock.sendto(TASK_TAG + json.dumps(
        task, separators=(",", ":")).encode(), addr)


def run(port, out, store, task_file=None, via=None):
    ingest = DurableIngest(store, out, via=via)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))
    sys.stderr.write("udp edge up: 0.0.0.0:%d → %s\n" % (port, out))
    offsets, queue, destinations = {}, {}, {}
    while True:
        poll_task_file(task_file, offsets, queue)
        frame, addr = sock.recvfrom(65535)
        try:
            node = frame_node(frame)
            if node:
                destinations[node] = addr
            ack = ingest.handle_frame(frame, "%s:%d" % addr)
            if ack:
                ack["edge_ts"] = time.time()
                sock.sendto(TASK_TAG + json.dumps(
                    ack, separators=(",", ":")).encode(), addr)
            for key, dest in node_task_dests(queue, node, destinations):
                for task in queue.get(key, ()):
                    send_task(sock, dest, task)
                queue.pop(key, None)
        except Exception as e:
            sys.stderr.write("ingest refused %s:%d: %s\n"
                             % (addr[0], addr[1], e))


def main():
    p = argparse.ArgumentParser(description="EcoCell durable UDP edge")
    p.add_argument("--port", type=int, default=4242)
    p.add_argument("--out", required=True, help="committed JSONL ledger")
    p.add_argument("--store", required=True, help="durable ingest dir")
    p.add_argument("--tasks", help="append-only node task JSONL")
    p.add_argument("--via", help="backhaul label stamped on committed "
                   "records (lora wifi cat1-sat starlink-sat)")
    a = p.parse_args()
    run(a.port, a.out, a.store, a.tasks, via=a.via)


if __name__ == "__main__":
    main()
