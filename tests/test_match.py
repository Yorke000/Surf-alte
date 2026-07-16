"""マッチングロジックのテスト。仕様書の例に基づく期待値を検証する。"""

from surf_feel.dictionary import load_boards, load_vocab
from surf_feel.match import nearest_vocab, rank_boards
from surf_feel.models import FeelVector


def _rank(feel: FeelVector) -> list[str]:
    boards = load_boards()
    vocab = load_vocab()
    return [m.board_id for m in rank_boards(feel, boards, vocab)]


def test_glide_hold_maps_to_mid_or_glider():
    """仕様書の例: グライド◎ ホールド◎ 反応性不要 → ミッド〜グライダー。"""
    feel = FeelVector(glide=0.9, flow=0.3, hold=0.85, loose=0.1, response=0.1, stillness=0.6)
    top2 = _rank(feel)[:2]
    assert set(top2) <= {"midlength", "glider", "log"}
    assert "midlength" in top2 or "glider" in top2


def test_loose_flow_maps_to_fish_or_twin():
    feel = FeelVector(glide=0.4, flow=0.8, hold=0.2, loose=0.9, response=0.5, stillness=0.1)
    top2 = _rank(feel)[:2]
    assert set(top2) & {"fish", "twin"}


def test_response_maps_to_performance():
    feel = FeelVector(glide=0.1, flow=0.4, hold=0.5, loose=0.4, response=0.95, stillness=0.0)
    assert _rank(feel)[0] == "performance"


def test_stillness_maps_to_log_or_glider():
    feel = FeelVector(glide=0.6, flow=0.1, hold=0.3, loose=0.05, response=0.05, stillness=0.95)
    assert _rank(feel)[0] in {"log", "glider"}


def test_nearest_vocab_returns_sorted():
    vocab = load_vocab()
    feel = FeelVector(glide=0.9, hold=0.8, stillness=0.6)
    hits = nearest_vocab(feel, vocab, top_k=5)
    assert len(hits) == 5
    sims = [s for _, s in hits]
    assert sims == sorted(sims, reverse=True)
    assert sims[0] > 0.8  # 近い語彙が存在する
