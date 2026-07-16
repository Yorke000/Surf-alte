"""蒸留パイプラインの機構テスト(API呼び出しなし)。"""

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "distill" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


prompts = _load("prompts")
distill = _load("distill")


def test_chunk_text_overlap():
    text = "a" * 15000
    chunks = distill.chunk_text(text, size=6000, overlap=400)
    assert len(chunks) == 3
    assert all(len(c) <= 6000 for c in chunks)
    # オーバーラップ分だけ前チャンクの末尾と次チャンクの先頭が重なる
    assert chunks[0][-400:] == chunks[1][:400]


def test_srt_to_text_strips_noise(tmp_path):
    fetch = _load("fetch_subtitles")
    srt = tmp_path / "x.srt"
    srt.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\nhello <b>world</b>\n\n"
        "2\n00:00:03,000 --> 00:00:05,000\nhello world\n\n"
        "3\n00:00:05,000 --> 00:00:07,000\nnext line\n",
        encoding="utf-8",
    )
    text = fetch.srt_to_text(srt)
    assert text == "hello world\nnext line"  # タグ除去+連続重複の排除


def test_merge_into_dictionary_dedupes(tmp_path, monkeypatch):
    from surf_feel.models import FeelVector, VocabEntry

    path = tmp_path / "vocab_distilled.json"
    monkeypatch.setattr(distill, "DISTILLED_PATH", path)

    e1 = VocabEntry(expression="テスト表現", feel_axes=FeelVector(glide=0.5), board_traits=["fish"])
    distill.merge_into_dictionary([e1])
    # 同じ表現は上書き(後勝ち)、別表現は追加
    e2 = VocabEntry(expression="テスト表現", feel_axes=FeelVector(glide=0.9), board_traits=["twin"])
    e3 = VocabEntry(expression="別の表現", feel_axes=FeelVector(hold=0.7), board_traits=["midlength"])
    distill.merge_into_dictionary([e2, e3])

    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["entries"]) == 2
    by_expr = {e["expression"]: e for e in data["entries"]}
    assert by_expr["テスト表現"]["feel_axes"]["glide"] == 0.9


def test_extract_schema_matches_vocab_entry():
    """抽出スキーマの必須フィールドが VocabEntry と一致していること。"""
    props = prompts.EXTRACT_SCHEMA["properties"]["entries"]["items"]["properties"]
    assert set(props) == {"expression", "feel_axes", "board_traits", "source"}
    axes = props["feel_axes"]["properties"]
    assert set(axes) == {"glide", "flow", "hold", "loose", "response", "stillness"}
