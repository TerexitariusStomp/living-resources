#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""drc_clean.py — iterative DRC-driven fragment cleanup.

Reads a kicad-cli DRC JSON report and removes the copper items that
violate, preferring dead-end fragments (which disconnect nothing).
Non-dead-end offenders are removed shortest-first and reported so a
re-route pass can heal the island.  Loops: DRC -> clean -> save.

usage: drc_clean.py board.kicad_pcb [--rounds N]
"""
import sys
import json
import math
import subprocess
import tempfile
import collections
import pcbnew

PCB = sys.argv[1]
ROUNDS = 4
if '--rounds' in sys.argv:
    ROUNDS = int(sys.argv[sys.argv.index('--rounds') + 1])

VIOL = {'shorting_items', 'tracks_crossing', 'clearance',
        'hole_clearance', 'items_not_allowed', 'copper_sliver',
        'holes_co_located', 'track_dangling', 'via_dangling'}


def run_drc():
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        path = f.name
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--format', 'json',
                    '-o', path, PCB],
                   check=True, capture_output=True)
    return json.load(open(path))


def junctions(item, pointmap, padpts, bodymap, nc):
    """count item endpoints that touch OTHER same-net copper.

    An endpoint is a junction when another same-net item's endpoint sits
    there, a pad sits there, or the endpoint lies on another same-net
    item's body (via-in-track etc.).  A dead-end fragment scores 0..1;
    a load-bearing link scores 2.
    """
    n = 0
    for (x, y) in endpoints(item):
        key = (round(x * 4), round(y * 4))
        if pointmap.get(key, 0) > 1 or padpts.get(key, 0):
            n += 1
            continue
        bx, by = int(x // 1.0), int(y // 1.0)
        for jx in (bx - 1, bx, bx + 1):
            for jy in (by - 1, by, by + 1):
                for ot in bodymap.get((nc, jx, jy), ()):
                    if ot is item:
                        continue
                    try:
                        sx1, sy1 = ot.GetStart().x / 1e6, ot.GetStart().y / 1e6
                        sx2, sy2 = ot.GetEnd().x / 1e6, ot.GetEnd().y / 1e6
                        dx, dy = sx2 - sx1, sy2 - sy1
                        L2 = dx * dx + dy * dy
                        tt = 0 if L2 == 0 else max(0, min(
                            1, ((x - sx1) * dx + (y - sy1) * dy) / L2))
                        dd = math.hypot(x - (sx1 + dx * tt),
                                        y - (sy1 + dy * tt))
                    except Exception:
                        px, py = ot.GetPosition().x / 1e6, \
                            ot.GetPosition().y / 1e6
                        dd = math.hypot(x - px, y - py)
                    if dd < 0.2:
                        n += 1
                        jx = jy = 99  # break outer loops
                if jx == 99:
                    break
            if jx == 99:
                break
    return n


def endpoints(item):
    try:
        return [(item.GetStart().x / 1e6, item.GetStart().y / 1e6),
                (item.GetEnd().x / 1e6, item.GetEnd().y / 1e6)]
    except Exception:
        return [(item.GetPosition().x / 1e6, item.GetPosition().y / 1e6)]


def length(item):
    try:
        s, e = item.GetStart(), item.GetEnd()
        return math.hypot((e.x - s.x) / 1e6, (e.y - s.y) / 1e6)
    except Exception:
        return 0.3


for rnd in range(ROUNDS):
    d = run_drc()
    viol = [x for x in d['violations'] if x['type'] in VIOL]
    if not viol:
        print('round', rnd, ': clean of target classes')
        break
    pairs = []
    for x in viol:
        uu = [i['uuid'] for i in x['items']]
        for i in range(len(uu)):
            for j in range(i + 1, len(uu)):
                pairs.append((uu[i], uu[j], x['type']))
    print('round', rnd, ':', len(viol), 'violations,',
          len(pairs), 'item pairs')
    board = pcbnew.LoadBoard(PCB)
    by_uuid = {}
    for t in board.GetTracks():
        by_uuid[t.m_Uuid.AsString()] = t
    # endpoint sharing map for leaf detection
    pointmap = collections.Counter()
    for t in by_uuid.values():
        for x, y in endpoints(t):
            pointmap[(round(x * 4), round(y * 4))] += 1
    padpts = collections.Counter()
    for fp in board.GetFootprints():
        for p in fp.Pads():
            padpts[(round(p.GetPosition().x / 1e6 * 4),
                    round(p.GetPosition().y / 1e6 * 4))] += 1
    # same-net item bodies, bucketed for the junction test
    bodymap = collections.defaultdict(list)
    for t in by_uuid.values():
        nc2 = t.GetNetCode()
        try:
            x1, y1 = t.GetStart().x / 1e6, t.GetStart().y / 1e6
            x2, y2 = t.GetEnd().x / 1e6, t.GetEnd().y / 1e6
            pts = [(x1, y1), (x2, y2)]
            n = max(1, int(math.hypot(x2 - x1, y2 - y1)))
            pts += [(x1 + (x2 - x1) * s / n, y1 + (y2 - y1) * s / n)
                    for s in range(1, n)]
        except Exception:
            pts = [(t.GetPosition().x / 1e6, t.GetPosition().y / 1e6)]
        for x, y in pts:
            bodymap[(nc2, int(x // 1.0), int(y // 1.0))].append(t)
    # score each item: how many violations it participates in
    score = collections.Counter()
    for a, b, ty in pairs:
        score[a] += 1
        score[b] += 1
    removed = 0
    live_pairs = collections.Counter()  # unordered pair -> count
    for a, b, ty in pairs:
        live_pairs[tuple(sorted((a, b)))] += 1
    # choose removals: for each pair, drop the item with the smaller
    # junction count (dead-end fragments first); ties -> most-violating.
    to_remove = set()
    for (a, b), cnt in live_pairs.items():
        if a in to_remove or b in to_remove:
            continue
        ia, ib = by_uuid.get(a), by_uuid.get(b)
        if ia is None and ib is None:
            continue
        if ia is None:
            to_remove.add(b)
            continue
        if ib is None:
            to_remove.add(a)
            continue
        ja = junctions(ia, pointmap, padpts, bodymap, ia.GetNetCode())
        jb = junctions(ib, pointmap, padpts, bodymap, ib.GetNetCode())
        # dead-end (0 junctions) always loses; otherwise most-violating,
        # then shortest
        cand = sorted(
            [(ja, -score[a], length(ia), a),
             (jb, -score[b], length(ib), b)])
        to_remove.add(cand[0][3])
    for u in to_remove:
        it = by_uuid.get(u)
        if it is not None:
            board.Remove(it)
            removed += 1
    # also remove danglers flagged outright
    print('  removed', removed, 'items')
    pcbnew.SaveBoard(PCB, board)

# final report
d = run_drc()
import collections as C
print('final:', C.Counter(x['type'] for x in d['violations']))
print('unconnected:', len(d.get('unconnected_items', [])))
