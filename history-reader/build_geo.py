# Build history-reader/geo.js — the real lng/lat base map for the 地理视图.
# Inputs (download to /tmp first; gitignored, not vendored):
#   china_prov.json : curl -s https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json -o /tmp/china_prov.json
#   ne10_rivers.json: curl -sL https://raw.githubusercontent.com/martynafford/natural-earth-geojson/master/10m/physical/ne_10m_rivers_lake_centerlines.json -o /tmp/ne10_rivers.json
# Output: window.HISTORY_GEO = { bbox, provinces:[[ [lng,lat],... ],...], rivers:{chang,huang,huai} }
# Clipped to BBOX + Douglas-Peucker decimated. Widen BBOX / add rivers if a new passage falls outside.

import json

# View window covering all three campaigns (Huai/Yangtze/Yellow basins)
BBOX = dict(w=104.0, e=122.5, s=28.0, n=42.0)
M = 0.6  # keep margin so clipped lines run to the edge

def inb(p):
    return (BBOX['w']-M) <= p[0] <= (BBOX['e']+M) and (BBOX['s']-M) <= p[1] <= (BBOX['n']+M)

def rdp(pts, tol):
    if len(pts) < 3: return pts[:]
    # iterative Douglas-Peucker
    keep=[False]*len(pts); keep[0]=keep[-1]=True
    stack=[(0,len(pts)-1)]
    import math
    def pd(p,a,b):
        ax,ay=a; bx,by=b; px,py=p
        dx,dy=bx-ax,by-ay
        if dx==0 and dy==0: return math.hypot(px-ax,py-ay)
        t=((px-ax)*dx+(py-ay)*dy)/(dx*dx+dy*dy)
        t=max(0,min(1,t)); cx,cy=ax+t*dx,ay+t*dy
        return math.hypot(px-cx,py-cy)
    while stack:
        a,b=stack.pop()
        if b<=a+1: continue
        dmax,idx=0,-1
        for i in range(a+1,b):
            d=pd(pts[i],pts[a],pts[b])
            if d>dmax: dmax,idx=d,i
        if dmax>tol:
            keep[idx]=True; stack.append((a,idx)); stack.append((idx,b))
    return [pts[i] for i in range(len(pts)) if keep[i]]

def clip_line(coords, tol):
    """Split a coord list into in-bbox runs, decimate each."""
    out=[]; run=[]
    for p in coords:
        if inb(p):
            run.append([round(p[0],3),round(p[1],3)])
        else:
            if len(run)>=2: out.append(rdp(run,tol))
            run=[]
    if len(run)>=2: out.append(rdp(run,tol))
    return out

def iter_lines(geom):
    t=geom['type']; c=geom['coordinates']
    if t=='LineString': yield c
    elif t=='MultiLineString':
        for l in c: yield l
    elif t=='Polygon':
        for ring in c: yield ring
    elif t=='MultiPolygon':
        for poly in c:
            for ring in poly: yield ring

# ---- provinces (faint outlines) ----
prov=json.load(open('/tmp/china_prov.json'))
SKIP={'台湾省','海南省','香港特别行政区','澳门特别行政区','100000_JD'}
prov_lines=[]
for f in prov['features']:
    name=f['properties']['name']
    if name in SKIP: continue
    for ring in iter_lines(f['geometry']):
        prov_lines += clip_line(ring, 0.09)  # coarse, they're just ghosts

# ---- rivers (from 10m) ----
riv=json.load(open('/tmp/ne10_rivers.json'))
want={'Yangtze':'chang','Chang Jiang':'chang','Huang':'huang','Huai':'huai'}
rivers={'chang':[], 'huang':[], 'huai':[]}
for f in riv['features']:
    nm=f['properties'].get('name') or ''
    key=want.get(nm)
    if not key: continue
    for line in iter_lines(f['geometry']):
        rivers[key]+= clip_line(line, 0.03)

# NE's Huai centerline ends ~116.5E; extend its real eastern course
# (正阳关→蚌埠→钟离/凤阳→盱眙→淮安) so 钟离 sits on the river.
rivers['huai'].append([
    [116.52,32.50],[116.80,32.66],[117.10,32.86],[117.36,32.93],
    [117.56,32.86],[117.90,33.01],[118.30,32.98],[118.62,33.06],[119.02,33.32]
])

def npts(ls): return sum(len(x) for x in ls)
print('province polylines:',len(prov_lines),'pts',npts(prov_lines))
for k,v in rivers.items(): print('river',k,'segs',len(v),'pts',npts(v))

out={'bbox':BBOX,'provinces':prov_lines,'rivers':rivers}
js='window.HISTORY_GEO='+json.dumps(out,separators=(',',':'),ensure_ascii=False)+';\n'
open('/home/zni/projects/chinese-character-teaching/history-reader/geo.js','w').write(js)
import os
print('geo.js bytes:', os.path.getsize('/home/zni/projects/chinese-character-teaching/history-reader/geo.js'))
