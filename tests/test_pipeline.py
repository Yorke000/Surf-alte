"""オフライン一気通貫テスト: 自由記述 → 翻訳 → マッチ → 提案。"""

from surf_feel.cli import main, render
from surf_feel.dictionary import load_boards, load_vocab
from surf_feel.match import rank_boards
from surf_feel.models import RiderProfile
from surf_feel.propose import build_proposal
from surf_feel.translate import translate_heuristic


HIGH_LINE_TEXT = "頭サイズの波でハイラインをただ走ってるだけで最高だった。何もしないでトリムが決まる感じ"
LOOSE_TEXT = "テールが抜けてドリフトしながらターンがつながるのが気持ちいい。キレより流す遊び"


def test_heuristic_translate_highline():
    feel = translate_heuristic(HIGH_LINE_TEXT)
    assert feel.hold > 0.5
    assert feel.stillness > 0.5
    assert feel.response < 0.3


def test_end_to_end_offline_highline():
    boards = load_boards()
    vocab = load_vocab()
    feel = translate_heuristic(HIGH_LINE_TEXT)
    ranked = rank_boards(feel, boards, vocab)
    proposal = build_proposal(
        HIGH_LINE_TEXT, feel, ranked, boards,
        RiderProfile(weight_kg=68), offline=True,
    )
    assert proposal.primary_board_id in {"midlength", "glider", "log"}
    assert proposal.dimensions.volume_min_l > 0
    assert proposal.feel_summary
    assert proposal.primary_reason

    out = render(proposal, boards)
    assert "第1候補" in out and "第2候補" in out and "使い分け" in out


def test_end_to_end_offline_loose():
    boards = load_boards()
    vocab = load_vocab()
    feel = translate_heuristic(LOOSE_TEXT)
    ranked = rank_boards(feel, boards, vocab)
    proposal = build_proposal(
        LOOSE_TEXT, feel, ranked, boards,
        RiderProfile(weight_kg=60, skill="advanced"), offline=True,
    )
    assert proposal.primary_board_id in {"fish", "twin"}
    # 第1候補と第2候補は別の板
    assert proposal.primary_board_id != proposal.secondary_board_id


def test_cli_offline(capsys):
    code = main(["--text", HIGH_LINE_TEXT, "--weight", "68", "--offline"])
    assert code == 0
    out = capsys.readouterr().out
    assert "あなたのフィール" in out
    assert "推奨ボリューム" in out
