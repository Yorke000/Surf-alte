"""YouTube 字幕の収集(Phase 1 のコーパス入口)。

yt-dlp で字幕(自動生成含む)をテキストとして distill/raw/ に保存する。
raw/ は .gitignore 済み — 元ソースは蒸留後に破棄する設計。

使い方:
    python distill/fetch_subtitles.py "https://www.youtube.com/watch?v=..."
    python distill/fetch_subtitles.py --channel "https://www.youtube.com/@needessentials" --limit 20
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent / "raw"


def fetch(url: str, limit: int | None = None, lang: str = "en") -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-auto-subs",
        "--write-subs",
        "--sub-langs", lang,
        "--convert-subs", "srt",
        "-o", str(RAW_DIR / "%(id)s.%(ext)s"),
    ]
    if limit:
        cmd += ["--playlist-end", str(limit)]
    cmd.append(url)
    subprocess.run(cmd, check=True)


def srt_to_text(srt_path: Path) -> str:
    """SRT からタイムスタンプ・番号・重複行を除去してプレーンテキスト化する。"""
    lines: list[str] = []
    prev = ""
    for line in srt_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.isdigit() or "-->" in line:
            continue
        line = re.sub(r"<[^>]+>", "", line)  # 自動字幕のタグ除去
        if line and line != prev:
            lines.append(line)
            prev = line
    return "\n".join(lines)


def convert_all() -> None:
    for srt in sorted(RAW_DIR.glob("*.srt")):
        txt = srt.with_suffix(".txt")
        txt.write_text(srt_to_text(srt), encoding="utf-8")
        print(f"converted: {txt.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="YouTube字幕を収集してテキスト化する")
    parser.add_argument("url", nargs="?", help="動画またはチャンネル/プレイリストのURL")
    parser.add_argument("--channel", help="チャンネルURL(url の代わりに)")
    parser.add_argument("--limit", type=int, help="取得する動画数の上限")
    parser.add_argument("--lang", default="en", help="字幕言語 (default: en)")
    parser.add_argument("--convert-only", action="store_true", help="既存 .srt のテキスト化のみ行う")
    args = parser.parse_args()

    if not args.convert_only:
        target = args.channel or args.url
        if not target:
            parser.error("URL か --channel を指定してください")
        fetch(target, limit=args.limit, lang=args.lang)
    convert_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())
