#!/usr/bin/env python3
"""都道府県名と市区町村名から代表座標（町丁目の平均）を返す。データ: geolonia/japanese-addresses
使い方: python3 tools/geocode.py 茨城県 つくば市"""
import json, sys, urllib.parse, urllib.request
BASE = 'https://raw.githubusercontent.com/geolonia/japanese-addresses/master/api/ja'
def geocode(pref, city):
    url = '%s/%s/%s.json' % (BASE, urllib.parse.quote(pref), urllib.parse.quote(city))
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            rows = json.load(r)
    except Exception:
        return None
    pts = [(float(x['lat']), float(x['lng'])) for x in rows if x.get('lat') and x.get('lng')]
    if not pts: return None
    # 外れ値に強いよう中央値を使う
    lats = sorted(p[0] for p in pts); lngs = sorted(p[1] for p in pts)
    return [round(lats[len(lats)//2], 4), round(lngs[len(lngs)//2], 4)]
if __name__ == '__main__':
    print(json.dumps(geocode(sys.argv[1], sys.argv[2])))
