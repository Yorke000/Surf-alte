"""Webフォーム(API)のテスト。実サーバーを立てて叩く。"""

import json
import threading
import urllib.request
import urllib.error

import pytest

from surf_feel.web import make_server


@pytest.fixture(scope="module")
def server_url():
    server = make_server(port=0, offline=True)  # port=0 で空きポートを取る
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


def _post(url: str, payload: dict) -> tuple[int, dict]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as res:
            return res.status, json.loads(res.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_index_served(server_url):
    with urllib.request.urlopen(f"{server_url}/") as res:
        assert res.status == 200
        body = res.read().decode("utf-8")
        assert "surf-feel" in body
        assert "気持ちよかった瞬間" in body


def test_propose_endpoint(server_url):
    status, data = _post(f"{server_url}/api/propose", {
        "text": "頭サイズのハイラインをただ走ってるだけで最高だった",
        "weight": 68,
        "skill": "intermediate",
        "freq": "weekly",
    })
    assert status == 200
    assert len(data["axes"]) == 6
    assert data["primary"]["name"]
    assert data["primary"]["dimensions"]["volume_min_l"] > 0
    assert data["secondary"]["name"] != data["primary"]["name"]
    assert data["offline"] is True


def test_propose_empty_text_returns_400(server_url):
    status, data = _post(f"{server_url}/api/propose", {"text": ""})
    assert status == 400
    assert "error" in data


def test_unknown_path_404(server_url):
    status, data = _post(f"{server_url}/api/nope", {})
    assert status == 404
