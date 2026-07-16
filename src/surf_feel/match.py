"""マッチングロジック。

1. ユーザーのフィールベクトルと語彙辞書エントリの近傍検索(コサイン類似度)
2. ヒットした語彙群に紐づくボード特性を集計
3. ボードタイプ自体のフィールプロファイルとの類似度も加味してランキング

MVPでは6軸ベクトルの直接比較で十分な精度が出るため embedding は使わない。
コーパス拡張(Phase 3)で表現数が増えたら Chroma への差し替えを検討する。
"""

from __future__ import annotations

from .dictionary import Board
from .models import BoardMatch, FeelVector, VocabEntry

# ボード自体のフィール類似度と、語彙経由の集計の混合比
BOARD_WEIGHT = 0.6
VOCAB_WEIGHT = 0.4


def nearest_vocab(
    feel: FeelVector, vocab: list[VocabEntry], top_k: int = 6
) -> list[tuple[VocabEntry, float]]:
    """フィールベクトルに近い語彙エントリを類似度付きで返す。"""
    scored = [(e, feel.cosine(e.feel_axes)) for e in vocab]
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:top_k]


def rank_boards(
    feel: FeelVector,
    boards: dict[str, Board],
    vocab: list[VocabEntry],
    top_k_vocab: int = 6,
) -> list[BoardMatch]:
    """フィールベクトルからボードタイプをランキングする。"""
    matched = nearest_vocab(feel, vocab, top_k=top_k_vocab)

    # 語彙経由の得票: 類似度を、その語彙が指すボード特性に配分する
    vocab_votes: dict[str, float] = {bid: 0.0 for bid in boards}
    vocab_hits: dict[str, list[VocabEntry]] = {bid: [] for bid in boards}
    for entry, sim in matched:
        for trait in entry.board_traits:
            if trait in boards:
                vocab_votes[trait] += sim
                vocab_hits[trait].append(entry)

    max_vote = max(vocab_votes.values()) or 1.0

    results: list[BoardMatch] = []
    for bid, board in boards.items():
        board_sim = feel.cosine(board.feel)
        vote = vocab_votes[bid] / max_vote
        score = BOARD_WEIGHT * board_sim + VOCAB_WEIGHT * vote
        results.append(
            BoardMatch(board_id=bid, score=score, matched_expressions=vocab_hits[bid])
        )
    results.sort(key=lambda m: m.score, reverse=True)
    return results
