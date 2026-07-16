"""自由記述 → フィール軸ベクトルへの翻訳。

メイン入力は「波乗り体験の中で一番気持ちよかった瞬間」の自由記述。
LLM がそれをフィール6軸のベクトルに翻訳する。

オフライン(APIキーなし・テスト)用に、キーワードベースの簡易翻訳も用意する。
"""

from __future__ import annotations

import os

from .axes import AXIS_INFO, AXIS_KEYS
from .models import FeelVector

DEFAULT_MODEL = os.environ.get("SURF_FEEL_MODEL", "claude-opus-4-8")


def _axes_rubric() -> str:
    return "\n".join(
        f"- {k}({AXIS_INFO[k]['label']}): {AXIS_INFO[k]['description']}"
        for k in AXIS_KEYS
    )


TRANSLATE_SYSTEM = f"""あなたはサーフィンのフィーリングを言語化する専門家です。
ユーザーが語る「波乗りで一番気持ちよかった瞬間」の自由記述を読み、
その体験がどのフィール軸に根ざしているかを 0.0〜1.0 でスコアリングしてください。

フィール軸の定義:
{_axes_rubric()}

スコアリングの方針:
- 記述に明確に現れているフィールは 0.7 以上を付ける
- 記述と矛盾するフィール(例: 「何もしないのが最高」なら response)は 0.2 以下に抑える
- 言及がなく判断できない軸は 0.3〜0.5 の中庸に置く
- 「速さ」への言及は、掘れた波の縦の速さなら response、走り続ける速さなら glide に振り分ける
- 全軸を高くしない。体験の核になっている軸を際立たせる
"""


def translate_with_claude(text: str, model: str = DEFAULT_MODEL) -> FeelVector:
    """Claude API で自由記述をフィールベクトルに翻訳する。"""
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.parse(
        model=model,
        max_tokens=2048,
        system=TRANSLATE_SYSTEM,
        messages=[{"role": "user", "content": text}],
        output_format=FeelVector,
    )
    parsed = response.parsed_output
    if parsed is None:
        raise RuntimeError("フィール軸への翻訳結果を取得できませんでした")
    return parsed


# --- オフライン用の簡易翻訳(キーワードマッチ) ---

_KEYWORDS: dict[str, list[str]] = {
    "glide": ["滑り出", "走り続け", "走ってる", "走って", "グライド", "スピードに乗", "一掻き", "パドルが軽", "うねりから", "伸びていく", "推進"],
    "flow": ["ターンがつなが", "途切れな", "線を描", "リズム", "流れるよう", "レールからレール", "連続", "つながる"],
    "hold": ["ハイライン", "レールが噛", "レールを入れ", "張り付", "安心感", "掘れた波", "レールを差し"],
    "loose": ["テールが抜け", "ドリフト", "ルース", "滑らせ", "流す", "レイバック", "遊び"],
    "response": ["キレ", "クイック", "縦に", "リップ", "即座", "反応", "切り返し", "アクション", "蹴った"],
    "stillness": ["何もしな", "静か", "ゆっくり", "トリム", "任せ", "ただ立って", "ただ走", "穏やか", "のんびり"],
}


def translate_heuristic(text: str) -> FeelVector:
    """キーワードベースの簡易翻訳。テスト・オフライン動作用。"""
    scores: dict[str, float] = {}
    for axis, words in _KEYWORDS.items():
        hits = sum(1 for w in words if w in text)
        scores[axis] = min(1.0, 0.3 + 0.35 * hits) if hits else 0.15
    return FeelVector(**scores)


def translate(text: str, offline: bool = False, model: str = DEFAULT_MODEL) -> FeelVector:
    if offline:
        return translate_heuristic(text)
    return translate_with_claude(text, model=model)
