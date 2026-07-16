"""提案文の生成。

出力時は語彙辞書を参照して LLM が自分の言葉で生成する(蒸留アーキテクチャ)。
元記事の表現がそのまま出ない構造 — 参照するのは辞書エントリのみで、
元ソースはそもそもアプリに存在しない。

オフライン時は辞書の語彙とボードカタログの記述からテンプレートで組み立てる。
"""

from __future__ import annotations

import json
import os

from pydantic import BaseModel, Field

from .axes import AXIS_INFO, AXIS_KEYS
from .dictionary import Board
from .models import BoardMatch, FeelVector, Proposal, RiderProfile
from .volume import recommend_dimensions

DEFAULT_MODEL = os.environ.get("SURF_FEEL_MODEL", "claude-opus-4-8")


class _Narrative(BaseModel):
    """LLM に生成させる文章パート。"""

    feel_summary: str = Field(description="ユーザーのフィールを3〜4文で言語化した文章")
    primary_reason: str = Field(description="第1候補がそのフィールに合う理由(3〜4文)")
    secondary_reason: str = Field(description="第2候補の紹介(2〜3文)")
    usage_note: str = Field(description="第1候補と第2候補の使い分け(2〜3文)")


PROPOSE_SYSTEM = """あなたはサーフボードのフィーリングに深い理解を持つアドバイザーです。
ユーザーの体験の言語化(フィール軸スコア)と、マッチしたフィール語彙辞書、
候補ボードの情報が与えられます。

以下を生成してください:
- feel_summary: ユーザー自身も言葉にできていなかったフィールを、本人が「そう、それだ」と思える形で言語化する
- primary_reason: なぜ第1候補の板がそのフィールに合うのか。ロッカー・アウトライン・フィンと感覚の因果で語る
- secondary_reason: 第2候補の紹介
- usage_note: 波や気分によるつかい分け

重要な方針:
- 辞書の語彙を参考にしつつ、必ず自分の言葉で書き直すこと。辞書の表現をそのままコピーしない
- 浮力が大きいことを欠点として扱わない。「浮力の余りはグライドの原資」という価値観で語る
- 数値やスペックは補足に留め、主語は常にフィール(どう気持ちいいか)にする
- 日本語で、押し付けがましくない文体で書く
"""


def _build_context(
    feel: FeelVector,
    primary: BoardMatch,
    secondary: BoardMatch,
    boards: dict[str, Board],
    profile: RiderProfile,
) -> str:
    def board_info(m: BoardMatch) -> dict:
        b = boards[m.board_id]
        return {
            "name": b.name,
            "character": b.character,
            "fin_setup": b.fin_setup,
            "fin_reason": b.fin_reason,
            "matched_vocab": [e.expression for e in m.matched_expressions],
        }

    context = {
        "feel_axes": {
            AXIS_INFO[k]["label"]: round(getattr(feel, k), 2) for k in AXIS_KEYS
        },
        "primary_board": board_info(primary),
        "secondary_board": board_info(secondary),
        "rider": {
            "weight_kg": profile.weight_kg,
            "skill": profile.skill,
            "wave_note": profile.wave_note,
            "frequency": profile.frequency,
        },
    }
    return json.dumps(context, ensure_ascii=False, indent=2)


def _narrative_with_claude(context: str, user_text: str, model: str) -> _Narrative:
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.parse(
        model=model,
        max_tokens=4096,
        system=PROPOSE_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"ユーザーの自由記述:\n{user_text}\n\n"
                    f"分析コンテキスト:\n{context}"
                ),
            }
        ],
        output_format=_Narrative,
    )
    parsed = response.parsed_output
    if parsed is None:
        raise RuntimeError("提案文の生成結果を取得できませんでした")
    return parsed


def _narrative_offline(
    feel: FeelVector,
    primary: BoardMatch,
    secondary: BoardMatch,
    boards: dict[str, Board],
) -> _Narrative:
    """テンプレートベースの組み立て。辞書語彙 + ボードカタログの記述を使う。"""
    p, s = boards[primary.board_id], boards[secondary.board_id]
    dom = [AXIS_INFO[k]["label"] for k in feel.dominant_axes(2)]
    hits = [e.expression for e in primary.matched_expressions[:2]]
    hit_text = "「" + "」「".join(hits) + "」" if hits else "その感覚"

    return _Narrative(
        feel_summary=(
            f"あなたの体験の核にあるのは{dom[0]}と{dom[1]}です。"
            f"辞書の語彙でいえば {hit_text} に近い感覚が、あなたの一番気持ちいい瞬間を支えています。"
        ),
        primary_reason=(
            f"{p.name}は、{p.character}。"
            f"フィンは{p.fin_setup} — {p.fin_reason}。"
        ),
        secondary_reason=f"第2候補は{s.name}。{s.character}。",
        usage_note=(
            f"普段のコンディションでは{p.name}を軸にし、"
            f"波質や気分が変わる日に{s.name}を持ち出す使い分けがおすすめです。"
        ),
    )


def build_proposal(
    user_text: str,
    feel: FeelVector,
    ranked: list[BoardMatch],
    boards: dict[str, Board],
    profile: RiderProfile,
    offline: bool = False,
    model: str = DEFAULT_MODEL,
) -> Proposal:
    primary, secondary = ranked[0], ranked[1]
    if offline:
        narrative = _narrative_offline(feel, primary, secondary, boards)
    else:
        context = _build_context(feel, primary, secondary, boards, profile)
        narrative = _narrative_with_claude(context, user_text, model)

    board = boards[primary.board_id]
    return Proposal(
        feel_vector=feel,
        feel_summary=narrative.feel_summary,
        primary_board_id=primary.board_id,
        primary_reason=narrative.primary_reason,
        fin_setup=board.fin_setup,
        dimensions=recommend_dimensions(profile, board),
        secondary_board_id=secondary.board_id,
        secondary_reason=narrative.secondary_reason,
        usage_note=narrative.usage_note,
    )
