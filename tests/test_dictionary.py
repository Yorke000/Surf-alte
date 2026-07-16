"""辞書・カタログの整合性テスト。"""

from surf_feel.dictionary import load_boards, load_vocab


def test_boards_load():
    boards = load_boards()
    assert set(boards) == {"fish", "twin", "midlength", "performance", "glider", "log"}
    for b in boards.values():
        assert b.volume_factor >= 1.0
        assert b.fin_setup
        for band in ("light", "mid", "heavy"):
            assert band in b.dims


def test_vocab_loads_and_traits_reference_known_boards():
    boards = load_boards()
    vocab = load_vocab()
    assert len(vocab) >= 20
    # 各エントリは少なくとも1つ、既知のボードIDを指していること
    for entry in vocab:
        board_ids = [t for t in entry.board_traits if t in boards]
        assert board_ids, f"ボードIDを含まない語彙: {entry.expression}"


def test_vocab_axes_in_range():
    for entry in load_vocab():
        for v in entry.feel_axes.as_list():
            assert 0.0 <= v <= 1.0
