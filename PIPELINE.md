# データ拡充パイプライン（定期実行用の手順書）

Searchuniv に全国の大学を少しずつ追加し、既存校の空欄（研究分野・取得できる資格・主な進路など）を埋めるための手順です。1時間ごとの定期実行がこの手順書を読んで1回分の作業をします。

## 全体像
- `data/master_list.json`：全国の大学の一覧（名前・設置区分・都道府県・公式サイト）。
- `data/queue.json`：これから処理する学校。`add` は新規追加、`enrich` は既存校の空欄補完。処理したら `done` に移す。
- `data/*.json`：ページのデータ本体。`tools/merge_batch.py` で取り込み、`tools/build.py` で `index.html` を作る。
- 公開ページ：Claude のアーティファクト（slug `8174544a-a178-4a35-a835-6e4a0156f302`、タイトル Searchuniv）。

## 1回の実行でやること
1. リポジトリ `tiimura6/searchuniv` を用意する（add_repo を access "push" で呼び、案内どおり clone）。
2. `data/queue.json` を読み、`add` の先頭から最大 **10校**、`enrich` の先頭から最大 **5校** を選ぶ。両方空なら「完了」と報告し、この定期実行（名前「Searchuniv データ拡充」）を update_trigger で無効化して終わる。
3. 各校の情報を集める（下の「集め方」）。WebFetch は1時間あたりの上限があるので、**WebFetch は合計60回まで**、WebSearch は合計30回まで。上限に当たったら、そこまでの分だけで先へ進む。
4. 集めた結果を `batches/<UTC日時>.json` に保存し、`python3 tools/merge_batch.py batches/<そのファイル>` を実行。表示された「要確認」は報告に含める。
5. 処理できた学校を `queue.json` の `add`/`enrich` から `done` へ移す（取れなかった学校は末尾に回す。同じ学校が3回失敗したら `failed` に移す）。
6. `python3 tools/build.py` で `index.html` を作り、`node --check` 相当のエラーがないことを確認（`python3 -c "s=open('index.html').read();open('/tmp/t.js','w').write(s.split('<script>')[1].split('</script>')[0])" && node --check /tmp/t.js`）。
7. コミットして main にプッシュ（コミットメッセージ例「データ拡充: 〇校追加・〇校補完」）。
8. 公開ページを更新：mcp__claude-artifacts__get_artifact で現在の version を確認 → list_files → publish_files（slug、base_version、files=[{"as":"index.html","path":"<clone先>/index.html"}]、mode "patch"）。
9. 追加・補完した件数と、残りの件数を短く報告。

## 集め方（1校あたり）
主な出典は河合塾 Kei-Net。大学ごとの4桁コードがある（例：筑波 1085、茨城 1065）。コードが分からなければ WebSearch で「〇〇大学 Kei-Net」を1回検索して特定する。次のページを WebFetch で開く（検索結果に出ていなくても直接開けることが多い）：
- `https://search.keinet.ne.jp/{コード}`（大学トップ：所在地・キャンパス・沿革）
- `https://search.keinet.ne.jp/outline/department/{コード}`（学部・学科、学生数、概要・特色）
- `https://search.keinet.ne.jp/{コード}/outline/licential`（取得可能資格）
- `https://search.keinet.ne.jp/{コード}/outline/admission_employment`（進学・就職実績）
- 余裕があれば `https://search.keinet.ne.jp/{コード}/general/exam_result`（一般選抜の「大学計」）とボーダー（偏差値・共テ得点率）
大学校・専門職大学で Kei-Net に無いものは、公式サイトから。

**事実は出典ページにあるものだけ。記憶や推測で埋めない。** 見つからない項目は空にする。特色・メモは出典の内容を自分の言葉で短くまとめる（丸写ししない）。

## batch の形式（JSON 配列）
```json
[{
  "name": "弘前大学",
  "cat": "national",            // national|public|private|daigakkou|senmon（既存校の enrich では省略可）
  "type": "国立",               // 国立|公立|私立|大学校の所管 など、カード表示用
  "pref": "青森県弘前市",        // カード表示用の所在地
  "pref_name": "青森県", "city": "弘前市",   // 座標用（本部キャンパスの市区町村）
  "features": ["特色1（1文）", "特色2", "特色3"],
  "memo": "担任向けメモ1〜2文（入試方式の特徴、地元枠、学費の安さなど出典で確認できたこと）",
  "reading": "ひろさき",        // 「大学」「大学校」「専門職大学」を除いた読み（ひらがな）
  "aliases": ["弘大"],          // よく使われる略称・旧称（確かなものだけ）
  "hp": "https://www.hirosaki-u.ac.jp/",
  "info": {
    "difficulty": {"hensachi": "42.5〜65.0", "kyotei": "52%〜82%", "year": "2027年度入試用"},
    "faculties": ["人文社会科学部", "..."],
    "students": {"count": 5800, "year": 2025},
    "founded": "1949年 新制大学",
    "access": "文京町キャンパス：JR弘前駅からバス約15分",
    "tuition": {"amount": 817800, "label": "入学金＋授業料", "year": 2026},
    "research": ["白神山地の生態系研究", "..."],
    "licenses": ["教員免許（中・高）", "看護師国家試験受験資格"],
    "careers": "公務員・教員・医療職が多い。",
    "notable": [], "news": [],
    "sources": ["https://search.keinet.ne.jp/1010", "..."]
  },
  "exam": {"general": {"year": 2026, "applicants": 0, "examinees": 0, "passers": 0, "ratio": 0.0},
           "format": "前期・後期を実施。…", "sources": ["..."]}
}]
```
- `features` は2〜3個、`memo` は必須（新規追加のとき）。
- `enrich` の既存校は、`name` と埋めたい `info` の項目だけでよい（既存の値は上書きされない）。
