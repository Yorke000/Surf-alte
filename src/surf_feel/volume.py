"""浮力・寸法のガードレール計算。

設計思想: 数値(浮力)は「間違えないためのガードレール」であって主語ではない。
「浮力の余り=悪」ではなく「浮力の余りはグライドの原資」として扱うため、
グライド系のボードほど volume_factor が大きく設定されている(boards.json)。
"""

from __future__ import annotations

from .dictionary import Board
from .models import DimensionRange, RiderProfile

# スキル別の基準浮力 (L/kg)。あくまで下限を外さないためのガードレール
BASE_L_PER_KG = {
    "beginner": 0.55,
    "intermediate": 0.42,
    "advanced": 0.36,
}

# 入水頻度による補正。ブランクが空くほど余裕を持たせる
FREQUENCY_FACTOR = {
    "weekly": 1.0,
    "monthly": 1.08,
    "rarely": 1.15,
}


def weight_band(weight_kg: float) -> str:
    if weight_kg < 60:
        return "light"
    if weight_kg <= 75:
        return "mid"
    return "heavy"


def recommend_dimensions(profile: RiderProfile, board: Board) -> DimensionRange:
    base = BASE_L_PER_KG[profile.skill] * profile.weight_kg
    center = base * board.volume_factor * FREQUENCY_FACTOR[profile.frequency]
    dims = board.dims[weight_band(profile.weight_kg)]
    return DimensionRange(
        volume_min_l=round(center * 0.93, 1),
        volume_max_l=round(center * 1.07, 1),
        length_range=dims["length"],
        width_range=dims["width"],
        thickness_range=dims["thickness"],
    )
