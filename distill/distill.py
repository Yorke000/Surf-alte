"""蒸留バッチ処理(Phase 1 の中核)。

収集済みテキスト(distill/raw/*.txt)をチャンク分割し、Claude API の
バッチ処理でフィール語彙を抽出、data/vocab_distilled.json に蓄積する。

RAGではない: 元テキストは辞書に入らない。抽出時に言い換えられた語彙
+フィール軸スコア+ボード特性のみが残り、元ソースは --purge-raw で破棄できる。

使い方:
    python distill/distill.py submit          # バッチ投入(batch_id が表示される)
    python distill/distill.py collect <batch_id>   # 結果回収→辞書へマージ
    python distill/distill.py collect <batch_id> --purge-raw  # 回収後に元ソースを破棄
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from prompts import EXTRACT_SCHEMA, EXTRACT_SYSTEM, extract_user_prompt  # noqa: E402
from surf_feel.models import VocabEntry  # noqa: E402

DISTILL_DIR = Path(__file__).resolve().parent
RAW_DIR = DISTILL_DIR / "raw"
DATA_DIR = DISTILL_DIR.parent / "data"
DISTILLED_PATH = DATA_DIR / "vocab_distilled.json"

MODEL = os.environ.get("SURF_FEEL_MODEL", "claude-opus-4-8")
CHUNK_CHARS = 6000
CHUNK_OVERLAP = 400


def chunk_text(text: str, size: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += size - overlap
    return chunks


def build_requests() -> list[Request]:
    requests: list[Request] = []
    for txt in sorted(RAW_DIR.glob("*.txt")):
        for i, chunk in enumerate(chunk_text(txt.read_text(encoding="utf-8"))):
            chunk_id = f"{txt.stem}-{i:03d}"
            requests.append(
                Request(
                    custom_id=chunk_id,
                    params=MessageCreateParamsNonStreaming(
                        model=MODEL,
                        max_tokens=4096,
                        system=EXTRACT_SYSTEM,
                        messages=[
                            {"role": "user", "content": extract_user_prompt(chunk_id, chunk)}
                        ],
                        output_config={
                            "format": {"type": "json_schema", "schema": EXTRACT_SCHEMA}
                        },
                    ),
                )
            )
    return requests


def submit() -> None:
    requests = build_requests()
    if not requests:
        print("distill/raw/ に .txt がありません。先に fetch_subtitles.py を実行してください。")
        sys.exit(1)
    client = anthropic.Anthropic()
    batch = client.messages.batches.create(requests=requests)
    print(f"バッチ投入完了: {batch.id}({len(requests)} チャンク)")
    print(f"回収コマンド: python distill/distill.py collect {batch.id}")


def collect(batch_id: str, purge_raw: bool = False, wait: bool = True) -> None:
    client = anthropic.Anthropic()

    if wait:
        while True:
            batch = client.messages.batches.retrieve(batch_id)
            if batch.processing_status == "ended":
                break
            counts = batch.request_counts
            print(f"処理中… succeeded={counts.succeeded} processing={counts.processing}")
            time.sleep(30)

    new_entries: list[VocabEntry] = []
    errors = 0
    for result in client.messages.batches.results(batch_id):
        if result.result.type != "succeeded":
            errors += 1
            continue
        msg = result.result.message
        text = next((b.text for b in msg.content if b.type == "text"), "")
        try:
            payload = json.loads(text)
            for e in payload.get("entries", []):
                e.setdefault("source", result.custom_id)
                new_entries.append(VocabEntry(**e))
        except (json.JSONDecodeError, ValueError) as exc:
            print(f"[warn] {result.custom_id}: パース失敗 ({exc})", file=sys.stderr)
            errors += 1

    merge_into_dictionary(new_entries)
    print(f"抽出 {len(new_entries)} 語彙 / エラー {errors} 件 → {DISTILLED_PATH}")

    if purge_raw:
        removed = 0
        for f in RAW_DIR.glob("*"):
            f.unlink()
            removed += 1
        print(f"元ソースを破棄しました({removed} ファイル)")


def merge_into_dictionary(new_entries: list[VocabEntry]) -> None:
    """表現をキーに重複排除しつつ vocab_distilled.json へマージする。"""
    existing: dict[str, dict] = {}
    if DISTILLED_PATH.exists():
        for e in json.loads(DISTILLED_PATH.read_text(encoding="utf-8")).get("entries", []):
            existing[e["expression"]] = e
    for entry in new_entries:
        existing[entry.expression] = entry.model_dump()
    DISTILLED_PATH.write_text(
        json.dumps({"entries": list(existing.values())}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="フィール語彙の蒸留バッチ処理")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("submit", help="raw/*.txt をチャンク分割してバッチ投入する")
    p_collect = sub.add_parser("collect", help="バッチ結果を回収して辞書にマージする")
    p_collect.add_argument("batch_id")
    p_collect.add_argument("--purge-raw", action="store_true", help="回収後に元ソースを削除する")
    p_collect.add_argument("--no-wait", action="store_true", help="完了待ちをしない")
    args = parser.parse_args()

    if args.command == "submit":
        submit()
    else:
        collect(args.batch_id, purge_raw=args.purge_raw, wait=not args.no_wait)
    return 0


if __name__ == "__main__":
    sys.exit(main())
