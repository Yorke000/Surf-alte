"""シンプルなWebフォーム(Phase 4)。

標準ライブラリのみで動く軽量サーバー。CLI と同じパイプラインを
POST /api/propose で提供し、static/index.html のフォームから叩く。

使い方:
    surf-feel-web            # http://localhost:8765
    surf-feel-web --port 8000 --offline
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .axes import AXIS_INFO, AXIS_KEYS
from .dictionary import load_boards, load_vocab
from .match import rank_boards
from .models import RiderProfile
from .propose import build_proposal
from .translate import translate

STATIC_DIR = Path(__file__).resolve().parent / "static"


def run_pipeline(payload: dict, offline: bool) -> dict:
    """フォーム入力 → 提案 JSON。CLI と同じ流れ。"""
    text = (payload.get("text") or "").strip()
    if not text:
        raise ValueError("自由記述(text)が空です")

    profile = RiderProfile(
        weight_kg=float(payload.get("weight") or 65),
        skill=payload.get("skill") or "intermediate",
        wave_note=payload.get("wave") or "",
        frequency=payload.get("freq") or "weekly",
    )

    boards = load_boards()
    vocab = load_vocab()
    feel = translate(text, offline=offline)
    ranked = rank_boards(feel, boards, vocab)
    proposal = build_proposal(text, feel, ranked, boards, profile, offline=offline)

    primary = boards[proposal.primary_board_id]
    secondary = boards[proposal.secondary_board_id]
    return {
        "axes": [
            {
                "key": k,
                "label": AXIS_INFO[k]["label"],
                "value": round(getattr(proposal.feel_vector, k), 2),
            }
            for k in AXIS_KEYS
        ],
        "feel_summary": proposal.feel_summary,
        "primary": {
            "name": primary.name,
            "reason": proposal.primary_reason,
            "fin_setup": proposal.fin_setup,
            "dimensions": proposal.dimensions.model_dump(),
        },
        "secondary": {
            "name": secondary.name,
            "reason": proposal.secondary_reason,
        },
        "usage_note": proposal.usage_note,
        "offline": offline,
    }


class Handler(BaseHTTPRequestHandler):
    offline: bool = False

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, code: int, obj: dict) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            html = (STATIC_DIR / "index.html").read_bytes()
            self._send(200, html, "text/html; charset=utf-8")
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/propose":
            self._send_json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            result = run_pipeline(payload, offline=self.offline)
            self._send_json(200, result)
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
        except Exception as exc:  # 予期しない失敗もフォームに返す
            self._send_json(500, {"error": f"{type(exc).__name__}: {exc}"})

    def log_message(self, fmt: str, *args) -> None:
        print(f"[web] {fmt % args}", file=sys.stderr)


def make_server(port: int, offline: bool) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"offline": offline})
    return ThreadingHTTPServer(("127.0.0.1", port), handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="surf-feel-web", description="Webフォームを起動する")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--offline", action="store_true",
                        help="Claude API を使わずに動かす(簡易翻訳+テンプレート生成)")
    args = parser.parse_args(argv)

    offline = args.offline
    if not offline and not (
        os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    ):
        print("(APIキーが見つからないため --offline モードで起動します)", file=sys.stderr)
        offline = True

    server = make_server(args.port, offline)
    mode = "offline" if offline else "Claude API"
    print(f"surf-feel web: http://localhost:{args.port}  (モード: {mode})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
