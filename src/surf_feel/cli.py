"""CLI エントリポイント。

使い方:
    surf-feel --text "頭サイズのハイラインをただ走ってるだけで最高だった" \\
              --weight 68 --skill intermediate --freq weekly

    surf-feel            # 対話モード
    surf-feel --offline  # APIキーなしで動かす(簡易翻訳+テンプレート生成)
"""

from __future__ import annotations

import argparse
import os
import sys

from .axes import AXIS_INFO, AXIS_KEYS
from .dictionary import load_boards, load_vocab
from .match import rank_boards
from .models import Proposal, RiderProfile
from .propose import build_proposal
from .translate import translate


def _bar(value: float, width: int = 20) -> str:
    filled = round(value * width)
    return "█" * filled + "░" * (width - filled)


def render(proposal: Proposal, boards) -> str:
    p = boards[proposal.primary_board_id]
    s = boards[proposal.secondary_board_id]
    d = proposal.dimensions

    lines = []
    lines.append("")
    lines.append("━━━ あなたのフィール ━━━")
    for k in AXIS_KEYS:
        v = getattr(proposal.feel_vector, k)
        lines.append(f"  {AXIS_INFO[k]['label']:　<6} {_bar(v)} {v:.2f}")
    lines.append("")
    lines.append(proposal.feel_summary)
    lines.append("")
    lines.append(f"━━━ 第1候補: {p.name} ━━━")
    lines.append(proposal.primary_reason)
    lines.append("")
    lines.append(f"  フィン      : {proposal.fin_setup}")
    lines.append(f"  推奨ボリューム: {d.volume_min_l}〜{d.volume_max_l} L")
    lines.append(f"  長さ        : {d.length_range}")
    lines.append(f"  幅          : {d.width_range}")
    lines.append(f"  厚み        : {d.thickness_range}")
    lines.append("")
    lines.append(f"━━━ 第2候補: {s.name} ━━━")
    lines.append(proposal.secondary_reason)
    lines.append("")
    lines.append("━━━ 使い分け ━━━")
    lines.append(proposal.usage_note)
    lines.append("")
    return "\n".join(lines)


def _interactive_input() -> tuple[str, RiderProfile]:
    print("波乗り体験の中で「一番気持ちよかった瞬間」を、思い出せる限り自由に書いてください。")
    print("(波のサイズ、何をしていたか、どこが気持ちよかったか…)\n")
    text = input("> ").strip()
    if not text:
        print("入力が空です。", file=sys.stderr)
        sys.exit(1)

    print("\n-- 以下は補正用の補助入力です(Enter でデフォルト) --")
    weight = input("体重 kg [65]: ").strip() or "65"
    skill = input("スキル beginner/intermediate/advanced [intermediate]: ").strip() or "intermediate"
    wave = input("ホームポイントの波質・サイズ(自由記述、省略可): ").strip()
    freq = input("入水頻度 weekly/monthly/rarely [weekly]: ").strip() or "weekly"

    profile = RiderProfile(
        weight_kg=float(weight), skill=skill, wave_note=wave, frequency=freq
    )
    return text, profile


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="surf-feel",
        description="言語化できないフィーリングを言語化し、それに合うボードを提案する",
    )
    parser.add_argument("--text", help="一番気持ちよかった瞬間の自由記述")
    parser.add_argument("--weight", type=float, default=65.0, help="体重 kg")
    parser.add_argument(
        "--skill", choices=["beginner", "intermediate", "advanced"], default="intermediate"
    )
    parser.add_argument("--wave", default="", help="ホームポイントの波質(自由記述)")
    parser.add_argument(
        "--freq", choices=["weekly", "monthly", "rarely"], default="weekly", help="入水頻度"
    )
    parser.add_argument(
        "--offline", action="store_true",
        help="Claude API を使わずに動かす(簡易翻訳+テンプレート生成)",
    )
    args = parser.parse_args(argv)

    if args.text:
        text = args.text
        profile = RiderProfile(
            weight_kg=args.weight, skill=args.skill,
            wave_note=args.wave, frequency=args.freq,
        )
    else:
        text, profile = _interactive_input()

    offline = args.offline
    if not offline and not (
        os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    ):
        print("(APIキーが見つからないため --offline モードで実行します)\n", file=sys.stderr)
        offline = True

    boards = load_boards()
    vocab = load_vocab()

    feel = translate(text, offline=offline)
    ranked = rank_boards(feel, boards, vocab)
    proposal = build_proposal(
        text, feel, ranked, boards, profile, offline=offline
    )
    print(render(proposal, boards))
    return 0


if __name__ == "__main__":
    sys.exit(main())
