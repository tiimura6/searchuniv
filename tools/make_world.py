"""世界地図（協定校の国を示す用）を作る。
入力: world-atlas の countries-110m.json、i18n-iso-countries の codes.json と langs/ja.json
出力: data/world.json {"w":幅,"h":高さ,"c":[[iso3, 日本語名, パス]...],"cent":{iso3:[x,y]},"ja":{日本語名/別名: iso3}}
投影: Natural Earth I（中心経度0）。南極は除く。"""
import json, math, sys
wa, codes_p, ja_p, out = sys.argv[1:5]
t = json.load(open(wa)); sx, sy = t['transform']['scale']; tx, ty = t['transform']['translate']
S, W, H = 150, 0, 0
def proj(lon, lat):
    l, p = math.radians(lon), math.radians(lat); p2 = p * p; p4 = p2 * p2
    x = l * (0.8707 - 0.131979 * p2 + p4 * (-0.013791 + p4 * (0.003971 * p2 - 0.001529 * p4)))
    y = p * (1.007226 + p2 * (0.015085 + p4 * (-0.044475 + 0.028874 * p2 - 0.005916 * p4)))
    return x * S, -y * S
arcs = []
for a in t['arcs']:
    x = y = 0; pts = []
    for dx, dy in a:
        x += dx; y += dy; pts.append((x * sx + tx, y * sy + ty))
    arcs.append(pts)
def ring(r):
    pts = []
    for i in r:
        seg = arcs[i] if i >= 0 else arcs[~i][::-1]
        pts.extend(seg if not pts else seg[1:])
    # 日付変更線をまたぐ輪（ロシア東端・フィジーなど）は、西経側の点を180度に寄せて横一文字の線が出ないようにする
    if any(lon > 150 for lon, _ in pts) and any(lon < -150 for lon, _ in pts):
        east = sum(1 for lon, _ in pts if lon > 0) >= len(pts) / 2
        pts = [((180 if east else -180) if (lon < 0) == east else lon, lat) for lon, lat in pts]
    return [proj(lon, lat) for lon, lat in pts]
X0 = proj(-180, 0)[0]; Y0 = proj(0, 85)[1]
codes = {c[2]: c for c in json.load(open(codes_p))}
jan = json.load(open(ja_p))['countries']
out_c = []; cent = {}; ja = {}
for g in t['objects']['countries']['geometries']:
    gid = g.get('id')
    if gid == '010' or gid not in codes: continue
    a2, a3 = codes[gid][0], codes[gid][1]
    names = jan.get(a2); names = names if isinstance(names, list) else [names]
    polys = g['arcs'] if g['type'] == 'MultiPolygon' else [g['arcs']]
    d = []; best = (0, None)
    for poly in polys:
        for k, r in enumerate(poly):
            pts = [(x - X0, y - Y0) for x, y in ring(r)]
            if k == 0:
                A = sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts))) / 2
                if abs(A) > best[0]:
                    cx = sum((pts[i][0] + pts[i - 1][0]) * (pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1]) for i in range(len(pts))) / (6 * A)
                    cy = sum((pts[i][1] + pts[i - 1][1]) * (pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1]) for i in range(len(pts))) / (6 * A)
                    best = (abs(A), [round(cx, 1), round(cy, 1)])
            prev = None; seg = []
            for x, y in pts:
                X, Y = round(x * 10), round(y * 10)
                if prev is None: seg.append('M%d %d' % (X, Y))
                elif (X, Y) != prev:
                    dx, dy = X - prev[0], Y - prev[1]
                    seg.append(('l' if len(seg) == 1 else ('' if dx < 0 else ' ')) + '%d%s%d' % (dx, '' if dy < 0 else ' ', dy))
                prev = (X, Y)
            if len(seg) > 2: d.append(''.join(seg) + 'z')
    out_c.append([a3, names[0], ''.join(d)]); cent[a3] = best[1]
    for n in names: ja[n] = a3
# 小さな国・地域（110mに形が無い）は中心点だけ
small = {'SGP': (103.8, 1.35), 'HKG': (114.17, 22.3), 'MAC': (113.55, 22.2), 'MLT': (14.4, 35.9), 'LUX': (6.13, 49.6), 'BHR': (50.55, 26.05), 'MDV': (73.5, 4.2), 'MUS': (57.55, -20.3), 'FJI': (178.0, -17.8), 'SMR': (12.45, 43.94), 'MCO': (7.42, 43.74), 'LIE': (9.55, 47.15), 'AND': (1.52, 42.5), 'VAT': (12.45, 41.9), 'GUM': (144.8, 13.45), 'WSM': (-172.1, -13.75), 'TON': (-175.2, -21.2), 'PLW': (134.5, 7.5), 'BRN': (114.7, 4.5), 'FSM': (158.2, 6.9)}
for a3, (lon, lat) in small.items():
    if a3 not in cent:
        x, y = proj(lon, lat); cent[a3] = [round(x - X0, 1), round(y - Y0, 1)]
        a2 = next((c[0] for c in codes.values() if c[1] == a3), None)
        names = jan.get(a2) if a2 else None
        if names:
            names = names if isinstance(names, list) else [names]
            for n in names: ja[n] = a3
# よく使う別名
for k, v in {'アメリカ': 'USA', '米国': 'USA', 'アメリカ合衆国': 'USA', 'イギリス': 'GBR', '英国': 'GBR', '韓国': 'KOR', '大韓民国': 'KOR', '中国': 'CHN', '中華人民共和国': 'CHN', '台湾': 'TWN', 'ロシア': 'RUS', 'ベトナム': 'VNM', 'チェコ': 'CZE', 'オランダ': 'NLD', 'ニュージーランド': 'NZL', 'オーストラリア': 'AUS', 'カナダ': 'CAN', 'ドイツ': 'DEU', 'フランス': 'FRA', 'イタリア': 'ITA', 'スペイン': 'ESP', 'スイス': 'CHE', 'スウェーデン': 'SWE', 'ノルウェー': 'NOR', 'デンマーク': 'DNK', 'フィンランド': 'FIN', 'ベルギー': 'BEL', 'オーストリア': 'AUT', 'ポーランド': 'POL', 'ハンガリー': 'HUN', 'アイルランド': 'IRL', 'ポルトガル': 'PRT', 'ギリシャ': 'GRC', 'トルコ': 'TUR', 'タイ': 'THA', 'マレーシア': 'MYS', 'インドネシア': 'IDN', 'フィリピン': 'PHL', 'シンガポール': 'SGP', 'インド': 'IND', '香港': 'HKG', 'マカオ': 'MAC', 'モンゴル': 'MNG', 'メキシコ': 'MEX', 'ブラジル': 'BRA', 'エジプト': 'EGY', 'イラン': 'IRN', 'ラオス': 'LAO', 'ミャンマー': 'MMR', 'カンボジア': 'KHM', 'バングラデシュ': 'BGD', 'ネパール': 'NPL', 'スリランカ': 'LKA', 'パキスタン': 'PAK', 'ウズベキスタン': 'UZB', 'カザフスタン': 'KAZ', 'ケニア': 'KEN', '南アフリカ': 'ZAF', 'アルゼンチン': 'ARG', 'チリ': 'CHL', 'ペルー': 'PER', 'コロンビア': 'COL', 'イスラエル': 'ISR', 'サウジアラビア': 'SAU', 'アラブ首長国連邦': 'ARE', 'UAE': 'ARE', 'ウクライナ': 'UKR', 'ルーマニア': 'ROU', 'ブルガリア': 'BGR', 'セルビア': 'SRB', 'クロアチア': 'HRV', 'スロベニア': 'SVN', 'スロバキア': 'SVK', 'エストニア': 'EST', 'ラトビア': 'LVA', 'リトアニア': 'LTU', 'アイスランド': 'ISL', 'ブルネイ': 'BRN', 'ボリビア': 'BOL', 'シリア': 'SYR', 'ベネズエラ': 'VEN', 'タンザニア': 'TZA', 'コンゴ民主共和国': 'COD', 'モルドバ': 'MDA', 'キルギス': 'KGZ', 'ラオス人民民主共和国': 'LAO', '北朝鮮': 'PRK', 'パレスチナ': 'PSE', 'コートジボワール': 'CIV', 'ミャンマー連邦': 'MMR', 'コンゴ': 'COG', 'ミクロネシア': 'FSM'}.items():
    if v in cent: ja[k] = v
W = round(-2 * X0, 1); H = round(-2 * Y0 + 0, 1)
json.dump({'w': W, 'h': round(proj(0, -60)[1] - Y0, 1), 'c': out_c, 'cent': cent, 'ja': ja}, open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('countries', len(out_c), 'bytes', sum(len(c[2]) for c in out_c), 'w', W)
