"""蒸留パイプラインの抽出プロンプト。

元テキストからフィール語彙を抽出し、フィール軸スコアとボード特性にペア化する。
抽出結果は「言い換え済み」の語彙であることが重要 — 元の文章表現をそのまま
保存しない構造にすることで、辞書に元記事の表現が残らないようにする。
"""

EXTRACT_SYSTEM = """あなたはサーフボードのフィーリング語彙を蒸留する専門家です。
与えられたテキスト(ボードレビュー、シェイパーの語り、字幕など)から、
「乗り味・フィーリング」を表す表現を抽出してください。

各表現について:
1. expression: フィールの核を保ったまま、あなた自身の日本語で言い換える。
   元テキストの文章をそのまま翻訳・コピーしてはいけない。感覚の中身だけを取り出して再構成する
2. feel_axes: 以下の6軸を 0.0〜1.0 でスコアリング
   - glide: パドル一掻きで滑り出す、波のパワーを溜めて走る感覚
   - flow: ターンとターンが途切れない、線がつながる感覚
   - hold: ハイラインを張ってレールが噛んでいる安心感
   - loose: テールが抜ける遊び、ドリフトの気持ちよさ
   - response: 足元で即座に向きが変わるキレ
   - stillness: 板の上で何もしなくていい感覚
3. board_traits: その感覚を生むボード特性。次のボードタイプIDが該当すれば含める:
   fish / twin / midlength / performance / glider / log
   加えてロッカー・アウトライン・フィン等の特性語(例: ピンテール、シングルフィン、ローロッカー)も可
4. source: 出典メモ(チャンクIDなど内部管理用)

対象外(抽出しない):
- 旅行記、選手の経歴、大会結果などフィールと無関係な内容
- 単なるスペックの列挙(フィーリングへの言及を伴わないもの)

フィール表現が1つも見つからないチャンクでは entries を空配列にしてください。
"""


def extract_user_prompt(chunk_id: str, text: str) -> str:
    return f"チャンクID: {chunk_id}\n\n--- テキスト ---\n{text}"


# 構造化出力用の JSON Schema(バッチAPIでは output_config.format を使う)
EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "entries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"},
                    "feel_axes": {
                        "type": "object",
                        "properties": {
                            "glide": {"type": "number"},
                            "flow": {"type": "number"},
                            "hold": {"type": "number"},
                            "loose": {"type": "number"},
                            "response": {"type": "number"},
                            "stillness": {"type": "number"},
                        },
                        "required": ["glide", "flow", "hold", "loose", "response", "stillness"],
                        "additionalProperties": False,
                    },
                    "board_traits": {"type": "array", "items": {"type": "string"}},
                    "source": {"type": "string"},
                },
                "required": ["expression", "feel_axes", "board_traits", "source"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["entries"],
    "additionalProperties": False,
}
