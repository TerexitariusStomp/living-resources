#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
zs = [z for z in b.Zones() if not z.GetIsRuleArea()]
for z in zs:
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
pcbnew.ZONE_FILLER(b).Fill(zs)
pcbnew.SaveBoard(sys.argv[1], b)
print('island removal -> ALWAYS on', len(zs), 'zones')
