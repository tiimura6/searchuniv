#!/usr/bin/env python3
"""data/*.json と tools/template.html から index.html を組み立てる。
使い方: python3 tools/build.py   （リポジトリのルートで実行）"""
import json, math, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda n: json.load(open(os.path.join(ROOT, 'data', n + '.json'), encoding='utf-8'))

# d3.geoAzimuthalEqualArea().center([138.5,35.7]).rotate([-138.5,-35.7]).scale(1700).translate([2500,-1930]) と同じ投影
LAM0, PHI0 = math.radians(138.5), math.radians(36 - 18/60)
def project(lat, lon):
    lam, phi = math.radians(lon) - LAM0, math.radians(lat)
    # 緯度方向の回転（rotate の第2成分）
    cosphi = math.cos(phi)
    x0, y0, z0 = cosphi*math.cos(lam), cosphi*math.sin(lam), math.sin(phi)
    # rotate around y-axis by -PHI0
    c, s = math.cos(PHI0), math.sin(PHI0)
    x1 = x0*c + z0*s; z1 = -x0*s + z0*c; y1 = y0
    lam1, phi1 = math.atan2(y1, x1), math.asin(max(-1, min(1, z1)))
    k = math.sqrt(2/(1+math.cos(phi1)*math.cos(lam1)))
    x = k*math.cos(phi1)*math.sin(lam1); y = k*math.sin(phi1)
    return [round(2500 + 1700*(x - CX), 1), round(-1930 - 1700*(y - CY), 1)]

def _raw(lam, phi):
    k = math.sqrt(2/(1+math.cos(phi)*math.cos(lam)))
    return k*math.cos(phi)*math.sin(lam), k*math.sin(phi)
# d3 の center は回転前の座標で生投影した点を translate に合わせる
CX, CY = _raw(math.radians(138.5), math.radians(36 - 18/60))

# ページを軽くするため、大学の詳細で開いたときに要る重いデータは別ファイルにして後から読み込む
LAZY = ('fdiff', 'schedule', 'money', 'partners', 'sources', '_checked', 'notable', 'news', 'access', 'founded', 'students', 'methods', 'eng', 'ratios', 'qtrend', 'oc')

def main():
    cards = D('cards'); exam = D('exam'); info = D('info'); hp = D('hp')
    read = D('readings'); alias = D('aliases'); coords = D('coords'); prefs = D('map_prefs')
    guide = D('guide') if os.path.exists(os.path.join(ROOT, 'data', 'guide.json')) else {}
    names = [c[0] for c in cards]
    if len(set(names)) != len(names):
        dup = sorted({n for n in names if names.count(n) > 1}); sys.exit('重複: %s' % dup)
    dots = {n: project(*coords[n]) for n in names if n in coords}
    t = open(os.path.join(ROOT, 'tools', 'template.html'), encoding='utf-8').read()
    J = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    rep = {
        'CARDS': ('/*CARDS*/', '/*END_CARDS*/', '[\n' + ',\n'.join(json.dumps(c, ensure_ascii=False) for c in cards) + '\n]'),
        'EXAM': ('/*EXAM_DATA*/', '/*END_EXAM*/', J({n: exam[n] for n in names if n in exam})),
        'INFO': ('/*INFO_DATA*/', '/*END_INFO*/', J({n: {k: v for k, v in info[n].items() if k not in LAZY} for n in names if n in info})),
        'MAP': ('/*MAP_DATA*/', '/*END_MAP*/', J({'prefs': prefs, 'dots': dots})),
        'HP': ('/*HP*/', '/*END_HP*/', J({n: hp[n] for n in names if hp.get(n)})),
        'READ': ('/*READ*/', '/*END_READ*/', J({n: read[n] for n in names if n in read})),
        'ALIAS': ('/*ALIAS*/', '/*END_ALIAS*/', J(alias)),
        'GUIDE': ('/*GUIDE*/', '/*END_GUIDE*/', J({n: guide[n] for n in names if n in guide})),
        'BUILD': ('/*BUILD*/', '/*END_BUILD*/', J({'built': __import__('datetime').datetime.now(__import__('datetime').timezone(__import__('datetime').timedelta(hours=9))).strftime('%Y-%m-%d %H:%M'),
                  'schedule': max([v.get('_checked', {}).get('schedule', '') for v in info.values()] + ['']),
                  'diffyear': next((v['difficulty'].get('year') for v in info.values() if (v.get('difficulty') or {}).get('year')), '')})),
    }
    for k, (a, b, v) in rep.items():
        pat = re.escape(a) + r'.*?' + re.escape(b)
        if not re.search(pat, t, re.S): sys.exit('テンプレートに %s がない' % k)
        t = re.sub(pat, lambda _m: a + v + b, t, count=1, flags=re.S)
    open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8').write(t)
    detail = {n: {k: info[n][k] for k in LAZY if k in info[n]} for n in names if n in info}
    detail = {n: v for n, v in detail.items() if v}
    open(os.path.join(ROOT, 'detail.json'), 'w', encoding='utf-8').write(json.dumps(detail, ensure_ascii=False, separators=(',', ':')))
    for src, dst in (('world', 'world.json'), ('map_muni', 'muni.json')):
        if os.path.exists(os.path.join(ROOT, 'data', src + '.json')):
            open(os.path.join(ROOT, dst), 'w', encoding='utf-8').write(json.dumps(D(src), ensure_ascii=False, separators=(',', ':')))
    miss = [n for n in names if n not in coords]
    print('built index.html (%dKB) + detail.json (%dKB): %d校 / 座標なし %d校 %s' % (len(t.encode())//1024, os.path.getsize(os.path.join(ROOT,'detail.json'))//1024, len(names), len(miss), miss[:10]))

if __name__ == '__main__':
    main()
