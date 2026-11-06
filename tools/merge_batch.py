#!/usr/bin/env python3
"""収集した学校データ（batches/*.json）を data/*.json に取り込む。
使い方: python3 tools/merge_batch.py batches/2026-11-06T07.json
batch の形式は PIPELINE.md を参照。既存校は info/exam の空欄だけを埋める（上書きしない）。"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geocode import geocode
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda n: os.path.join(ROOT, 'data', n + '.json')
L = lambda n: json.load(open(P(n), encoding='utf-8'))
def W(n, o): json.dump(o, open(P(n), 'w', encoding='utf-8'), ensure_ascii=False, indent=0, separators=(',', ': '))
CATS = {'national','public','private','daigakkou','senmon','teidai','kanto','chiho','souke','march','kankan','chuken','rikou','iryo','joshi','kokusai','ibaraki'}
def empty(v): return v is None or v == '' or v == [] or v == {} or (isinstance(v, dict) and not any(v.values()))
def main(path):
    batch = json.load(open(path, encoding='utf-8'))
    cards, info, exam, hp, read, alias, coords = L('cards'), L('info'), L('exam'), L('hp'), L('readings'), L('aliases'), L('coords')
    names = {c[0] for c in cards}; added = filled = 0; problems = []
    for r in batch:
        n = r.get('name', '').strip()
        if not n: continue
        if n not in names:
            feats = [f for f in r.get('features', []) if f][:3]
            if r.get('cat') not in CATS or len(feats) < 2 or not r.get('memo'):
                problems.append(n + ': cat/features/memo 不足'); continue
            cards.append([n, r['cat'], r.get('type', ''), r.get('pref', ''), feats, r['memo']])
            names.add(n); added += 1
        if r.get('hp') and not hp.get(n): hp[n] = r['hp']
        if r.get('reading') and n not in read: read[n] = r['reading']
        if r.get('aliases'):
            alias[n] = sorted(set(alias.get(n, []) + [a for a in r['aliases'] if a]))
        if n not in coords:
            c = r.get('latlng') or (geocode(r.get('pref_name', ''), r.get('city', '')) if r.get('city') else None)
            if c: coords[n] = c
            else: problems.append(n + ': 座標なし')
        cur = info.setdefault(n, {})
        for k, v in (r.get('info') or {}).items():
            if k == 'sources':
                cur['sources'] = list(dict.fromkeys((cur.get('sources') or []) + [u for u in v if isinstance(u, str)]))
            elif empty(cur.get(k)) and not empty(v):
                cur[k] = v; filled += 1
        if r.get('exam'):
            e = exam.setdefault(n, {})
            for k, v in r['exam'].items():
                if empty(e.get(k)) and not empty(v): e[k] = v
    for n, o in [('cards', cards), ('info', info), ('exam', exam), ('hp', hp), ('readings', read), ('aliases', alias), ('coords', coords)]:
        W(n, o)
    print('追加 %d校 / 既存校の空欄を %d 項目補完 / 合計 %d校' % (added, filled, len(cards)))
    for p in problems: print('  要確認:', p)
if __name__ == '__main__':
    main(sys.argv[1])
