# データ拡充パイプライン（定期実行用の手順書）

> 優先順位（2026-11-06 決定）：`add` は国立→公立→私立の順に並べてある。並び順を崩さず先頭から処理すること。失敗して末尾に回す場合も、国公立はその種別の最後尾（私立より前）に戻す。

Searchuniv に全国の大学を少しずつ追加し、既存校の空欄（研究分野・取得できる資格・主な進路など）を埋めるための手順です。1時間ごとの定期実行がこの手順書を読んで1回分の作業をします。

## 全体像
- `data/master_list.json`：全国の大学の一覧（名前・設置区分・都道府県・公式サイト）。
- `data/queue.json`：これから処理する学校。`add` は新規追加、`enrich` は既存校の空欄補完。処理したら `done` に移す。
- `data/*.json`：ページのデータ本体。`tools/merge_batch.py` で取り込み、`tools/build.py` で `index.html` を作る。
- 公開ページ：Claude のアーティファクト（slug `8174544a-a178-4a35-a835-6e4a0156f302`、タイトル Searchuniv）。

## 1回の実行でやること
1. リポジトリ `tiimura6/searchuniv` を用意する（add_repo を access "push" で呼び、案内どおり clone）。
2. `data/queue.json` を読み（add の各項目は `{name,type,pref,hp,cat}`。cat と hp はそのまま batch に使う。名前に括弧付きの区分（例「（通信制のみ）」「（大学院のみ）」）がある学校は、その名前をそのまま batch の name に使い、項目に note があれば従う）、`add` の先頭から最大 **10校**、`enrich` の先頭から最大 **8校** を選ぶ（enrich の各項目は `{name, keinet, need}`。`need` に挙がった項目だけを集める：licenses は `/outline/licential`、careers は `/outline/admission_employment`、research は `outline/department/{コード}` の概要・特色）。両方空のときは、`complete` が true なら「全件完了」と報告してこの定期実行（名前「Searchuniv データ拡充」）を update_trigger で無効化する。`complete` が false なら何も変更せず「待機中（キュー準備中）」と報告して終わる（無効化しない）。
3. 各校の情報を集める（下の「集め方」）。WebFetch は1時間あたりの上限があるので、**WebFetch は合計60回まで（目安：新規1校5回、補完1校1〜3回）**、WebSearch は合計30回まで。上限に当たったら、そこまでの分だけで先へ進む。
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
- `https://search.keinet.ne.jp/{コード}/general/exam_subject`（共通テストの教科・科目数と英語リーディング:リスニングの配点 → info.kyotsu。R:Lは整数比に約分、例 100:100→"1:1"、160:40→"4:1"）
- **学部・学科（info.departments）**：`tools/DEPT_SPEC.md` の形で、学部ごとの学科・課程・専攻を Kei-Net `/outline/department` から集める。enrich の need に departments があるときも同じ手順。
- **海外協定校（info.partners）**：`tools/PARTNER_SPEC.md` の形で、大学公式の協定校一覧から国ごとの校数と代表校を数える（大学校は不要）。取れなければ enrich に need ["partners"] で積む。
- **入試方式（info.methods）**：`tools/METHODS_SPEC.md` の形で、一般選抜（国公立は前期・後期の共テ科目・二次科目・共テ:二次の配点比）、私立の共テ利用、学校推薦型（公募・指定校）、総合型をまとめる。`/general/exam_subject`、`/recommend/exam_rec`（推薦）、`/recommend/exam_ao`（総合型）を使う。ページが途中で切れたら大学公式の募集要項やマナビジョンで補う。取れなかったら enrich に `{name, keinet, need:["methods"]}` で積んで後回しにしてよい。enrich の need に methods があるときも同じ手順。
  - need に **methods_gap** があるとき：data/info.json のその校の methods（list と note）を読み、「未確認」「切れて確認できず」と書かれた方式・学部や、無い推薦（公募）・総合型を、大学公式の入試ページ・募集要項（PDF可）、マナビジョン、パスナビで確認する。batch では `info.methods_add` に {"list": [足す・直す行だけ], "note": "直した後の note 全文", "summary": "必要なら新しい要約"} を書く（同じ区分・方式名の行は置き換わる）。確認できたものだけ書き、確認できなければ何も書かず done に移す。
- 余裕があれば `https://search.keinet.ne.jp/{コード}/general/exam_result`（一般選抜の「大学計」）とボーダー（偏差値・共テ得点率）
大学校・専門職大学で Kei-Net に無いものは、公式サイトから。

### 使ってよい出典
- 河合塾 Kei-Net（主）
- 旺文社パスナビ
- ベネッセ ハイスクールオンライン（教員向け。ログイン不要で公開されているページのみ）、ベネッセ マナビジョン
- 大学公式サイト（入試結果・募集要項・大学概要・資格・就職のページ）
- 大学ポートレート（大学改革支援・学位授与機構）、文部科学省
出典が食い違うときは大学公式を優先し、batch の info.sources にどの出典を使ったか残す。

**事実は出典ページにあるものだけ。記憶や推測で埋めない。** 見つからない項目は空にする。特色・メモは出典の内容を自分の言葉で短くまとめる（丸写ししない）。

## batch の形式（JSON 配列）
```json
[{
  "name": "弘前大学",
  "cat": "national",            // national|public|private|daigakkou|senmon（既存校の enrich では省略可）
  "type": "国立",               // 国立|公立|私立|大学校の所管 など、カード表示用
  "pref": "青森県弘前市",        // カード表示用の所在地
  "pref_name": "青森県", "city": "弘前市",   // 座標用（本部キャンパスの市区町村）。必須。政令市は区まで（例「さいたま市浦和区」）。pref も「県＋市区町村」で書く
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
    "kyotsu": {"kamoku": "5教科7科目〜6教科8科目", "kyoka": [5, 6], "rl": ["1:1"], "rl_text": "全学部でR:L=1:1", "note": "", "year": "2027年度入試"},
    "licenses": ["教員免許（中・高）", "看護師国家試験受験資格"],
    "careers": "公務員・教員・医療職が多い。",
    "notable": [], "news": [],
    "sources": ["https://search.keinet.ne.jp/1010", "..."]
  },
  "guide": {"fit": "向いている生徒像1〜2文", "ask": ["面談で生徒に確認したいこと（40字以内）", "…（2〜3個）"], "caution": "注意点1文（なければ空）"},
  "exam": {"general": {"year": 2026, "applicants": 0, "examinees": 0, "passers": 0, "ratio": 0.0},
           "format": "前期・後期を実施。…", "sources": ["..."]}
}]
```
- `features` は2〜3個、`memo` と `city` は必須（新規追加のとき）。
- `guide` は新規追加のとき必須。集めたデータ（学部・特色・入試方式・学費・進路）だけを根拠に、担任が面談で使う形で書く（断定的な評価語は使わない）。
- `enrich` の既存校は、`name` と埋めたい `info` の項目だけでよい（既存の値は上書きされない）。
