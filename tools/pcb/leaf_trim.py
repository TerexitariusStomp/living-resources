# SPDX-License-Identifier: AGPL-3.0-or-later
# Iterative leaf-trim: remove copper tips that don't sole-connect a pad.
import sys,math,collections
import pcbnew
bd=sys.argv[1]
b=pcbnew.LoadBoard(bd)
CU=[0,2,4,6]
GS=0.15

items={}   # uuid -> dict(kind,obj,net,cells:set,ends:[(l,x,y)])
adj=collections.defaultdict(set)
cellmap=collections.defaultdict(set)

def reg(uid,l,gx,gy):
    cellmap[(l,gx,gy)].add(uid)

def add_item(t):
    uid=t.m_Uuid.AsString()
    if isinstance(t,pcbnew.PCB_VIA):
        x,y=t.GetPosition().x/1e6,t.GetPosition().y/1e6
        cs=set()
        r=0.35
        for l in CU:
            for gx in range(int((x-r)/GS),int((x+r)/GS)+1):
                for gy in range(int((y-r)/GS),int((y+r)/GS)+1):
                    if math.hypot(gx*GS-x,gy*GS-y)<=r: cs.add((l,gx,gy))
        items[uid]=dict(obj=t,kind='via',net=t.GetNetCode(),cells=cs,ends=[])
        try: items[uid]['shape']=t.GetEffectiveShape(CU[0])
        except: items[uid]['shape']=None
        for c in cs: reg(uid,*c)
        return
    s,e=t.GetStart(),t.GetEnd()
    x1,y1,x2,y2=s.x/1e6,s.y/1e6,e.x/1e6,e.y/1e6
    l=t.GetLayer()
    L=max(1e-9,math.hypot(x2-x1,y2-y1)); r=0.14
    cs=set()
    n=max(1,int(L/(GS/2)))
    for k in range(n+1):
        x,y=x1+(x2-x1)*k/n,y1+(y2-y1)*k/n
        for gx in range(int((x-r)/GS),int((x+r)/GS)+1):
            for gy in range(int((y-r)/GS),int((y+r)/GS)+1):
                if math.hypot(gx*GS-x,gy*GS-y)<=r: cs.add((l,gx,gy))
    items[uid]=dict(obj=t,kind='track',net=t.GetNetCode(),cells=cs,
                    endpts=[(l,x1,y1),(l,x2,y2)])
    try: items[uid]['shape']=t.GetEffectiveShape(l)
    except: items[uid]['shape']=None
    for c in cs: reg(uid,*c)

def add_pad(p):
    uid=p.m_Uuid.AsString()
    cs=set()
    for l in set(p.GetLayerSet().Seq())&set(CU):
        try: sh=p.GetEffectiveShape(l)
        except: continue
        bb=p.GetBoundingBox()
        x0,x1=bb.GetLeft()/1e6,bb.GetRight()/1e6
        y0,y1=bb.GetTop()/1e6,bb.GetBottom()/1e6
        for gx in range(int(x0/GS)-1,int(x1/GS)+2):
            for gy in range(int(y0/GS)-1,int(y1/GS)+2):
                pt=pcbnew.VECTOR2I(int(gx*GS*1e6),int(gy*GS*1e6))
                try:
                    if sh.Collide(pt,0): cs.add((l,gx,gy))
                except: pass
    items[uid]=dict(obj=p,kind='pad',net=p.GetNetCode(),cells=cs,ends=[],
                    layers=set(p.GetLayerSet().Seq())&set(CU),pos=p.GetPosition())
    items[uid]['shapes']={}
    for l in items[uid]['layers']:
        try: items[uid]['shapes'][l]=p.GetEffectiveShape(l)
        except: pass
    for c in cs: reg(uid,*c)

for t in b.GetTracks(): add_item(t)
for f in b.GetFootprints():
    for p in f.Pads(): add_pad(p)
print('items:',len(items))

for c,us in cellmap.items():
    us=list(us)
    for i in range(len(us)):
        for j in us[i+1:]:
            if items[us[i]]['net']==items[j]['net']:
                adj[us[i]].add(j); adj[j].add(us[i])

# pad touches same-net pour? (cached)
pour_by_netlayer={}
for z in b.Zones():
    if z.GetIsRuleArea(): continue
    pour_by_netlayer[(z.GetNetCode(),z.GetLayer())]=z.GetFilledPolysList(z.GetLayer())
def pad_on_pour(uid):
    it=items[uid]
    for l in it['layers']:
        fp=pour_by_netlayer.get((it['net'],l))
        if not fp: continue
        if fp.Contains(it['pos']): return True
    return False

def touches(l,x,y,uid):
    it=items[uid]
    pt=pcbnew.VECTOR2I(int(x*1e6),int(y*1e6))
    cands=set()
    gx,gy=int(x/GS),int(y/GS)
    for dx in (-1,0,1):
        for dy in (-1,0,1):
            cands|=cellmap.get((l,gx+dx,gy+dy),set())
    for u in cands:
        if u==uid or u not in items: continue
        nb=items[u]
        if nb['net']!=it['net']: continue
        if nb['kind']=='pad':
            sh=nb['shapes'].get(l)
        else:
            sh=nb.get('shape')
            if sh is not None and nb['kind']=='track' and (l,)!=(l,): pass
        if sh is None: continue
        try:
            if sh.Collide(pt,1000): return True   # within 1um
        except: continue
    return False

def is_leaf(uid):
    it=items[uid]
    if it['kind']=='via':
        return len(adj[uid])<=1
    if it['kind']!='track': return False
    for (l,x,y) in it.get('endpts',()):
        if not touches(l,x,y,uid): return True
    return False

removed=0
for rnd in range(40):
    leaves=[u for u in list(items) if items[u]['kind'] in('track','via') and is_leaf(u)]
    if not leaves: break
    prog=0
    for u in leaves:
        if u not in items: continue
        # safe? no neighbor that is a pad whose only links are {u} + pour-less
        safe=True
        for nb in adj[u]:
            if nb not in items: continue
            if items[nb]['kind']=='pad':
                others=[x for x in adj[nb] if x!=u and x in items]
                if not others and not pad_on_pour(nb): safe=False; break
        if not safe: continue
        # remove
        it=items.pop(u)
        for c in it['cells']:
            s=cellmap.get(c)
            if s: s.discard(u)
        for nb in adj.pop(u,set()):
            adj[nb].discard(u)
        b.Remove(it['obj']); removed+=1; prog+=1
    if prog==0: break
    print('round',rnd,'trimmed',prog)
print('total removed:',removed)
zs=[z for z in b.Zones() if not z.GetIsRuleArea()]
pcbnew.ZONE_FILLER(b).Fill(zs)
pcbnew.SaveBoard(bd,b)
