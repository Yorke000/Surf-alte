# surf-feel — サーフボード・フィール提案アプリ

**言語化できないフィーリングを言語化し、それに合うボードを提案する**アプリ。

浮力計算ベースの従来型ボードセレクター(if文的ロジック)ではなく、判断の主語を「フィール」に置く。浮力・長さ・厚みは結果として出す。「浮力の余り=悪」ではなく「浮力の余りはグライドの原資」と再定義する。

詳細な設計は [docs/spec.md](docs/spec.md) を参照。

## 仕組み

```
「一番気持ちよかった瞬間」の自由記述
  ↓ LLM(Claude API)がフィール6軸ベクトルに翻訳
  ↓ 蒸留済みフィール語彙辞書との近傍検索
  ↓ 語彙に紐づくボード特性を集計してランキング
  ↓ 補助入力(体重・スキル・入水頻度)で浮力レンジを補正(ガードレール)
  ↓ LLMが辞書の語彙を参照して「自分の言葉で」提案文を生成
```

### フィール軸(6項目)

| 軸 | 説明 |
|---|---|
| グライド感 | パドル一掻きで滑り出す、波のパワーを溜めて走る感覚 |
| フロー感 | ターンとターンが途切れない、線がつながる感覚 |
| ホールド感 | ハイラインを張ってレールが噛んでいる安心感 |
| ルース感 | テールが抜ける遊び、ドリフトの気持ちよさ |
| 反応性 | 足元で即座に向きが変わるキレ |
| 静けさ | 板の上で何もしなくていい感覚 |

## セットアップ

```bash
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...   # 未設定でも --offline で動く
```

## 使い方

```bash
# ワンショット
surf-feel --text "頭サイズのハイラインをただ走ってるだけで最高だった" \
          --weight 68 --skill intermediate --freq weekly

# 対話モード
surf-feel

# APIキーなしで試す(キーワード翻訳+テンプレート生成)
surf-feel --text "テールが抜けてドリフトするのが気持ちいい" --offline
```

### Webフォーム

```bash
surf-feel-web              # http://localhost:8765
surf-feel-web --port 8000 --offline
```

自由記述と補助入力を1画面で受け付け、フィール6軸の可視化・第1/第2候補・使い分けまで表示する。追加依存なし(標準ライブラリのHTTPサーバー+静的HTML)。

出力: フィール6軸の言語化 → 第1候補・第2候補のボードタイプ、フィンセットアップと選定理由、推奨ボリューム(L)・長さ・幅・厚みのレンジ、使い分けの提案。

## 語彙の蒸留パイプライン(RAGではない)

元記事をそのまま格納・引用するのではなく、**語彙の蒸留**方式を採用している。

- ストレージに残るのは元テキストではなく、抽出済みのフィール語彙辞書(`data/vocab_seed.json` / `data/vocab_distilled.json`)
- 抽出時に表現を言い換えて再構成するため、元記事の文章表現が辞書に残らない
- 元ソースは蒸留処理後に破棄できる(`--purge-raw`)

```bash
pip install yt-dlp

# 1. 字幕収集(例: Needessentials — Phase 1 の単一ソース検証)
python distill/fetch_subtitles.py --channel "https://www.youtube.com/@needessentials" --limit 20

# 2. チャンク分割 → Claude APIバッチ処理でフィール語彙を抽出
python distill/distill.py submit
# → batch_id が表示される

# 3. 結果回収 → 辞書へマージ → 元ソース破棄
python distill/distill.py collect <batch_id> --purge-raw
```

蒸留された語彙は次回の `surf-feel` 実行から自動的にマッチング対象になる。

## 開発

```bash
pip install -e ".[dev]"
pytest
```

テストはすべてオフライン(APIキー不要)で動く。

## 構成

```
src/surf_feel/
  axes.py        フィール6軸の定義
  models.py      FeelVector / VocabEntry / Proposal などのデータモデル
  translate.py   自由記述 → フィール軸ベクトル(Claude API / オフライン簡易版)
  dictionary.py  語彙辞書・ボードカタログのロード
  match.py       近傍検索+ボード特性の集計ランキング
  volume.py      浮力・寸法のガードレール計算
  propose.py     提案文の生成(Claude API / テンプレート)
  cli.py         CLIエントリポイント
  web.py         Webフォームサーバー(標準ライブラリのみ)
  static/        フォームのHTML
data/
  vocab_seed.json      シード語彙辞書
  vocab_distilled.json 蒸留パイプラインの出力(生成される)
  boards.json          ボードタイプカタログ
distill/
  fetch_subtitles.py   YouTube字幕収集(yt-dlp)
  prompts.py           抽出プロンプト+JSONスキーマ
  distill.py           バッチ投入・回収・辞書マージ
```

## ロードマップ

- [x] **Phase 1**: 蒸留パイプライン(字幕収集→バッチ抽出→JSON語彙辞書)
- [x] **Phase 2**: 自由記述→フィール軸翻訳→辞書マッチング→提案生成の一気通貫CLI
- [ ] **Phase 3**: コーパス拡張(Stab、Surfer's Journal、Swaylock's)+ 語彙数増加時の embedding / Chroma 導入(蒸留の実走には `ANTHROPIC_API_KEY` が必要)
- [x] **Phase 4**: Webフォーム化(`surf-feel-web`)、第2候補・使い分け提案
