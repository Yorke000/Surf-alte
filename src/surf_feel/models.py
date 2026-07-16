"""データモデル。

FeelVector が全モジュール共通の通貨。自由記述も、語彙辞書のエントリも、
ボードタイプの性格も、すべて同じ6軸ベクトルに翻訳して突き合わせる。
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, Field

from .axes import AXIS_KEYS


class FeelVector(BaseModel):
    """フィール6軸のスコア(各 0.0〜1.0)。"""

    glide: float = Field(0.0, ge=0.0, le=1.0, description="グライド感")
    flow: float = Field(0.0, ge=0.0, le=1.0, description="フロー感")
    hold: float = Field(0.0, ge=0.0, le=1.0, description="ホールド感")
    loose: float = Field(0.0, ge=0.0, le=1.0, description="ルース感")
    response: float = Field(0.0, ge=0.0, le=1.0, description="反応性")
    stillness: float = Field(0.0, ge=0.0, le=1.0, description="静けさ")

    def as_list(self) -> list[float]:
        return [getattr(self, k) for k in AXIS_KEYS]

    def cosine(self, other: "FeelVector") -> float:
        a, b = self.as_list(), other.as_list()
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def dominant_axes(self, n: int = 2) -> list[str]:
        """スコアの高い順に軸キーを返す。"""
        return sorted(AXIS_KEYS, key=lambda k: getattr(self, k), reverse=True)[:n]


class VocabEntry(BaseModel):
    """蒸留済みのフィール語彙。元記事の表現ではなく、抽出・再構成した言い回し。"""

    expression: str = Field(description="フィールを表す言い回し(自前の言葉)")
    feel_axes: FeelVector
    board_traits: list[str] = Field(default_factory=list, description="対応するボード特性・タイプID")
    source: str = Field(default="", description="出典メモ(内部管理用、出力には使わない)")


SkillLevel = Literal["beginner", "intermediate", "advanced"]
Frequency = Literal["weekly", "monthly", "rarely"]


class RiderProfile(BaseModel):
    """補助入力。フィールが主語、これは補正のためのガードレール。"""

    weight_kg: float = Field(65.0, gt=20, lt=200)
    skill: SkillLevel = "intermediate"
    wave_note: str = Field(default="", description="ホームポイントの波質・サイズの自由記述")
    frequency: Frequency = "weekly"


class BoardMatch(BaseModel):
    """マッチング結果1件。"""

    board_id: str
    score: float
    matched_expressions: list[VocabEntry] = Field(default_factory=list)


class DimensionRange(BaseModel):
    volume_min_l: float
    volume_max_l: float
    length_range: str
    width_range: str
    thickness_range: str


class Proposal(BaseModel):
    """最終出力。フィールの言語化 + ボード提案。"""

    feel_vector: FeelVector
    feel_summary: str = Field(description="ユーザーのフィールを言語化した文章")
    primary_board_id: str
    primary_reason: str
    fin_setup: str
    dimensions: DimensionRange
    secondary_board_id: str
    secondary_reason: str
    usage_note: str = Field(default="", description="第2候補との使い分け")
