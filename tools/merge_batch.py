#!/usr/bin/env python3
"""収集した学校データ（batches/*.json）を data/*.json に取り込む。
使い方: python3 tools/merge_batch.py batches/2026-11-06T07.json
batch の形式は PIPELINE.md を参照。既存校は info/exam の空欄だけを埋める（上書きしない）。"""
import datetime
TODAY = datetime.date.today().isoformat()
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
    guide = L('guide') if os.path.exists(P('guide')) else {}
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
            else:
                caps = json.load(open(P('pref_capitals'), encoding='utf-8')) if os.path.exists(P('pref_capitals')) else {}
                pn = r.get('pref_name') or next((k for k in caps if (r.get('pref') or '').startswith(k)), '')
                if caps.get(pn):
                    coords[n] = caps[pn]; problems.append(n + ': 市区町村が不明のため県庁所在地に仮置き（要修正）')
                else:
                    problems.append(n + ': 座標なし')
        cur = info.setdefault(n, {})
        for k, v in (r.get('info') or {}).items():
            if k.endswith('_replace') and not empty(v):
                # 既存の値を新しい値で置き換える（例：schedule_replace で入試日程を最新版に）
                base = k[:-len('_replace')]; cur[base] = v; filled += 1; cur.setdefault('_checked', {})[base] = TODAY
                continue
            if k == 'departments_full' and isinstance(v, list) and v:
                # 専攻・コースまで含めた学部・学科一覧で置き換える
                cur['departments'] = v; filled += 1; cur.setdefault('_checked', {})['departments'] = TODAY
                continue
            if k == 'methods_add' and isinstance(v, dict):
                # 既存の入試方式に足りない行を足す（同じ区分・方式名の行は新しい内容で置き換える）
                m = cur.setdefault('methods', {'list': []}); ML = m.setdefault('list', [])
                for row in v.get('list') or []:
                    key = (row.get('kubun'), row.get('name'))
                    idx = next((i for i, x in enumerate(ML) if (x.get('kubun'), x.get('name')) == key), None)
                    if idx is None: ML.append(row)
                    else: ML[idx] = row
                    filled += 1
                order = {'一般': 0, '共テ利用': 1, '推薦': 2, '総合型': 3, 'その他': 4}
                ML.sort(key=lambda x: order.get(x.get('kubun'), 9))
                for kk in ('summary', 'note', 'year'):
                    if v.get(kk): m[kk] = v[kk]
                continue
            if k == 'sources':
                cur['sources'] = list(dict.fromkeys((cur.get('sources') or []) + [u for u in v if isinstance(u, str)]))
            elif empty(cur.get(k)) and not empty(v):
                cur[k] = v; filled += 1
                cur.setdefault('_checked', {})[k] = TODAY
        if r.get('guide') and n not in guide:
            guide[n] = {k: r['guide'].get(k) for k in ('fit', 'ask', 'caution') if r['guide'].get(k)}
        if r.get('exam'):
            e = exam.setdefault(n, {})
            for k, v in r['exam'].items():
                if empty(e.get(k)) and not empty(v): e[k] = v
    for n, o in [('cards', cards), ('info', info), ('exam', exam), ('hp', hp), ('readings', read), ('aliases', alias), ('coords', coords), ('guide', guide)]:
        W(n, o)
    print('追加 %d校 / 既存校の空欄を %d 項目補完 / 合計 %d校' % (added, filled, len(cards)))
    for p in problems: print('  要確認:', p)
if __name__ == '__main__':
    main(sys.argv[1])
