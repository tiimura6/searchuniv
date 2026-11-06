"""市町村の境界線（同じ県内の市町村どうしの境目）と市町村名ラベルを作る。
入力: jpn-atlas の japan.json（地図と同じ投影済み座標）、code4fukui/localgovjp の CSV（名前・緯度経度）、
      国土地理院 地球地図日本 polbnda_jpn.dbf（人口：ラベルの優先順位用）
出力: data/map_muni.json  {"mesh": "<SVGパス>", "labels": [[名前, x, y, 人口], ...]}
"""
import json, sys, csv, struct, os
sys.path.insert(0, os.path.dirname(__file__))
from build import project
atlas, csvp, dbfp, out = sys.argv[1:5]
t = json.load(open(atlas))
sx, sy = t['transform']['scale']; tx, ty = t['transform']['translate']
arcs = []
for a in t['arcs']:
    x = y = 0; pts = []
    for dx, dy in a:
        x += dx; y += dy; pts.append((x * sx + tx, y * sy + ty))
    arcs.append(pts)
use = {}
for g in t['objects']['municipalities']['geometries']:
    polys = g['arcs'] if g['type'] == 'MultiPolygon' else [g['arcs']]
    for poly in polys:
        for ring in poly:
            for i in ring:
                use.setdefault(i if i >= 0 else ~i, set()).add(g['id'])
parts = []
for i, ids in use.items():
    if len(ids) < 2: continue
    ids = list(ids)
    if any(a[:2] != ids[0][:2] for a in ids): continue   # 県境は県の地図で描いている
    pts = arcs[i]
    # 0.1単位の整数・相対座標で短く（描画時に scale(0.1) をかける）
    prev = None; d = []
    for (x, y) in pts:
        X, Y = round(x * 10), round(y * 10)
        if prev is None: d.append('M%d %d' % (X, Y))
        elif (X, Y) != prev:
            dx, dy = X - prev[0], Y - prev[1]
            d.append(('l' if len(d) == 1 else ('' if dx < 0 else ' ')) + '%d%s%d' % (dx, '' if dy < 0 else ' ', dy))
        prev = (X, Y)
    if len(d) > 1: parts.append(''.join(d))
mesh = ''.join(parts)
# 人口
pop = {}
f = open(dbfp, 'rb'); h = f.read(32); n, hl, rl = struct.unpack('<IHH', h[4:12]); fields = []
while True:
    d = f.read(32)
    if d[0] == 0x0D: break
    fields.append((d[:11].split(b'\0')[0].decode(), d[16]))
f.seek(hl)
for _ in range(n):
    r = f.read(rl); pos = 1; o = {}
    for nm, l in fields: o[nm] = r[pos:pos + l].decode('utf-8', 'replace').strip(); pos += l
    try: pop[int(o['adm_code'])] = max(pop.get(int(o['adm_code']), 0), int(o['pop'] or 0))
    except ValueError: pass
labels = []
for row in csv.DictReader(open(csvp, encoding='utf-8-sig')):
    if ' ' in row['city'] or not row['lat']: continue     # 政令市の区は省く
    cid = int(row['cid'])
    if cid % 1000 == 0: continue                          # 県そのもの
    x, y = project(float(row['lat']), float(row['lng']))
    labels.append([row['city'], x, y, pop.get(cid, 0)])
labels.sort(key=lambda l: -l[3])
json.dump({'mesh': mesh, 'labels': labels}, open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('mesh %d bytes, labels %d' % (len(mesh), len(labels)))
