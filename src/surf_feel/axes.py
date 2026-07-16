"""フィール軸の定義。

このアプリの判断の主語は数値(浮力)ではなく「フィール」。
6軸すべて 0.0〜1.0 のスコアで表現する。
"""

from __future__ import annotations

# 軸の内部名(FeelVector のフィールド名と一致させる)
AXIS_KEYS: list[str] = [
    "glide",
    "flow",
    "hold",
    "loose",
    "response",
    "stillness",
]

# 表示名と、LLM がスコアリングするときの判断基準
AXIS_INFO: dict[str, dict[str, str]] = {
    "glide": {
        "label": "グライド感",
        "description": "パドル一掻きで滑り出す、波のパワーを溜めて走る感覚",
    },
    "flow": {
        "label": "フロー感",
        "description": "ターンとターンが途切れない、線がつながる感覚",
    },
    "hold": {
        "label": "ホールド感",
        "description": "ハイラインを張ってレールが噛んでいる安心感",
    },
    "loose": {
        "label": "ルース感",
        "description": "テールが抜ける遊び、ドリフトの気持ちよさ",
    },
    "response": {
        "label": "反応性",
        "description": "足元で即座に向きが変わるキレ",
    },
    "stillness": {
        "label": "静けさ",
        "description": "板の上で何もしなくていい感覚",
    },
}


def axis_label(key: str) -> str:
    return AXIS_INFO[key]["label"]
