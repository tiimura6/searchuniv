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
parts = {}
bbox = {}
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
    if len(d) > 1:
        pf = ids[0][:2]; parts.setdefault(pf, []).append(''.join(d))
        b = bbox.setdefault(pf, [1e9, 1e9, -1e9, -1e9])
        for (x, y) in pts: b[0] = min(b[0], x); b[1] = min(b[1], y); b[2] = max(b[2], x); b[3] = max(b[3], y)
mesh = [{'p': pf, 'b': [round(v, 1) for v in bbox[pf]], 'd': ''.join(v)} for pf, v in sorted(parts.items())]
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
# 県庁所在地（太字で表示）
CAPS = {(p, c) for c, p in (x.split(' ') for x in '札幌市 北海道,青森市 青森県,盛岡市 岩手県,仙台市 宮城県,秋田市 秋田県,山形市 山形県,福島市 福島県,水戸市 茨城県,宇都宮市 栃木県,前橋市 群馬県,さいたま市 埼玉県,千葉市 千葉県,新宿区 東京都,横浜市 神奈川県,新潟市 新潟県,富山市 富山県,金沢市 石川県,福井市 福井県,甲府市 山梨県,長野市 長野県,岐阜市 岐阜県,静岡市 静岡県,名古屋市 愛知県,津市 三重県,大津市 滋賀県,京都市 京都府,大阪市 大阪府,神戸市 兵庫県,奈良市 奈良県,和歌山市 和歌山県,鳥取市 鳥取県,松江市 島根県,岡山市 岡山県,広島市 広島県,山口市 山口県,徳島市 徳島県,高松市 香川県,松山市 愛媛県,高知市 高知県,福岡市 福岡県,佐賀市 佐賀県,長崎市 長崎県,熊本市 熊本県,大分市 大分県,宮崎市 宮崎県,鹿児島市 鹿児島県,那覇市 沖縄県'.split(','))}
labels = []
for row in csv.DictReader(open(csvp, encoding='utf-8-sig')):
    if ' ' in row['city'] or not row['lat']: continue     # 政令市の区は省く
    cid = int(row['cid'])
    if cid % 1000 == 0: continue                          # 県そのもの
    x, y = project(float(row['lat']), float(row['lng']))
    labels.append([row['city'], x, y, pop.get(cid, 0), 1 if (row['pref'], row['city']) in CAPS else 0])
labels.sort(key=lambda l: (-l[4], -l[3]))
json.dump({'mesh': mesh, 'labels': labels}, open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('mesh %d bytes, labels %d, capitals %d' % (sum(len(m['d']) for m in mesh), len(labels), sum(l[4] for l in labels)))
