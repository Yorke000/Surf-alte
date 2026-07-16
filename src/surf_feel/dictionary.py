"""語彙辞書とボードカタログのロード。

ストレージに残るのは元テキストではなく、抽出済みのフィール語彙辞書
(vocab_seed.json + distill パイプラインが追記する vocab_distilled.json)。
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import FeelVector, VocabEntry

# リポジトリ直下の data/ を既定とする
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

SEED_PATH = DATA_DIR / "vocab_seed.json"
DISTILLED_PATH = DATA_DIR / "vocab_distilled.json"
BOARDS_PATH = DATA_DIR / "boards.json"


class Board:
    def __init__(self, raw: dict):
        self.id: str = raw["id"]
        self.name: str = raw["name"]
        self.feel = FeelVector(**raw["feel"])
        self.fin_setup: str = raw["fin_setup"]
        self.fin_reason: str = raw["fin_reason"]
        self.volume_factor: float = raw["volume_factor"]
        self.character: str = raw["character"]
        self.dims: dict = raw["dims"]


def load_boards(path: Path = BOARDS_PATH) -> dict[str, Board]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {b["id"]: Board(b) for b in raw["boards"]}


def load_vocab(
    seed_path: Path = SEED_PATH,
    distilled_path: Path = DISTILLED_PATH,
) -> list[VocabEntry]:
    """シード辞書と蒸留済み辞書をマージして返す。表現の重複は後勝ちで除去。"""
    entries: dict[str, VocabEntry] = {}
    for path in (seed_path, distilled_path):
        if not path.exists():
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        for e in raw.get("entries", []):
            entry = VocabEntry(**e)
            entries[entry.expression] = entry
    return list(entries.values())
