# Copyright 2026 polite-http contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for polite_http.

A tiny in-process HTTP server backs the integration-style tests so the suite
runs fully offline.
"""

from __future__ import annotations

import gzip
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import polite_http
from polite_http import HttpClient, HttpError, HttpResponse
from polite_http.http_client import (
    _parse_retry_after,
    _parse_throttle_control,
    _RateLimiter,
)


class _Handler(BaseHTTPRequestHandler):
    """Request handler driven by a routing table on the server instance."""

    def log_message(self, *args):  # noqa: D102 - silence test server logging.
        pass

    def _dispatch(self):
        routes = self.server.routes  # type: ignore[attr-defined]
        handler = routes.get(self.path.split("?")[0])
        if handler is None:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found")
            return
        handler(self)

    do_GET = _dispatch
    do_POST = _dispatch


def _respond(handler, status, body, headers=None, gzip_body=False):
    if isinstance(body, str):
        body = body.encode("utf-8")
    handler.send_response(status)
    for key, value in (headers or {}).items():
        handler.send_header(key, value)
    if gzip_body:
        body = gzip.compress(body)
        handler.send_header("Content-Encoding", "gzip")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


@pytest.fixture()
def server():
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    httpd.routes = {}  # type: ignore[attr-defined]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address
    httpd.base_url = f"http://{host}:{port}/"  # type: ignore[attr-defined]
    try:
        yield httpd
    finally:
        httpd.shutdown()
        thread.join()


def _client(server, **kwargs):
    kwargs.setdefault("qps", 1000)
    kwargs.setdefault("jitter", 0.0)
    kwargs.setdefault("backoff_base", 0.0)
    return HttpClient(server.base_url, **kwargs)  # type: ignore[attr-defined]


def test_public_api_surface():
    for name in [
        "HttpClient",
        "HttpError",
        "HttpResponse",
        "RETRYABLE_STATUS_CODES",
        "USER_AGENT_ENV_VAR",
        "__version__",
    ]:
        assert hasattr(polite_http, name)


def test_fetch_json(server):
    server.routes["/data"] = lambda h: _respond(
        h, 200, json.dumps({"ok": True}), {"Content-Type": "application/json"}
    )
    client = _client(server)
    assert client.fetch_json("data") == {"ok": True}


def test_fetch_text_and_bytes(server):
    server.routes["/hello"] = lambda h: _respond(h, 200, "hi there")
    client = _client(server)
    assert client.fetch_text("hello") == "hi there"
    assert client.fetch_bytes("hello") == b"hi there"


def test_fetch_returns_response_object(server):
    server.routes["/r"] = lambda h: _respond(h, 200, "body")
    resp = _client(server).fetch("r")
    assert isinstance(resp, HttpResponse)
    assert resp.status_code == 200
    assert resp.text == "body"
    assert "HttpResponse(status=200" in repr(resp)


def test_gzip_response_is_decompressed(server):
    server.routes["/gz"] = lambda h: _respond(
        h, 200, "compressed payload", gzip_body=True
    )
    assert _client(server).fetch_text("gz") == "compressed payload"


def test_post_json_body(server):
    received = {}

    def handler(h):
        length = int(h.headers.get("Content-Length", 0))
        received["body"] = h.rfile.read(length)
        received["content_type"] = h.headers.get("Content-Type")
        _respond(h, 200, json.dumps({"ok": True}))

    server.routes["/submit"] = handler
    client = _client(server)
    client.fetch_json("submit", method="POST", json_body={"x": 1})
    assert json.loads(received["body"]) == {"x": 1}
    assert received["content_type"] == "application/json"


def test_retries_then_succeeds(server):
    state = {"n": 0}

    def handler(h):
        state["n"] += 1
        if state["n"] < 3:
            _respond(h, 503, "try again")
        else:
            _respond(h, 200, "ok")

    server.routes["/flaky"] = handler
    client = _client(server, max_retries=5)
    assert client.fetch_text("flaky") == "ok"
    assert state["n"] == 3


def test_non_retryable_raises_http_error(server):
    server.routes["/missing"] = lambda h: _respond(h, 404, "nope")
    client = _client(server)
    with pytest.raises(HttpError) as exc_info:
        client.fetch("missing")
    assert exc_info.value.status_code == 404
    assert exc_info.value.body == b"nope"


def test_retries_exhausted_raises(server):
    server.routes["/always500"] = lambda h: _respond(h, 500, "boom")
    client = _client(server, max_retries=2)
    with pytest.raises(HttpError) as exc_info:
        client.fetch("always500")
    assert exc_info.value.status_code == 500


def test_http_error_json_body():
    err = HttpError("oops", status_code=400, body=b'{"error": "bad"}')
    assert err.json() == {"error": "bad"}


def test_stream_lines(server):
    payload = "alpha\nbeta\ngamma\n"
    server.routes["/lines"] = lambda h: _respond(h, 200, payload)
    client = _client(server)
    assert list(client.stream_lines("lines")) == ["alpha", "beta", "gamma"]


def test_stream_bytes(server):
    server.routes["/blob"] = lambda h: _respond(h, 200, b"0123456789")
    client = _client(server)
    chunks = list(client.stream_bytes("blob", chunk_size=4))
    assert b"".join(chunks) == b"0123456789"


def test_data_and_json_body_mutually_exclusive(server):
    client = _client(server)
    with pytest.raises(ValueError):
        client.fetch("x", data=b"a", json_body={"b": 1})


def test_absolute_url_must_match_base_url(server):
    client = _client(server)
    with pytest.raises(ValueError):
        client.fetch("https://elsewhere.example.com/path")


def test_invalid_base_url_rejected():
    with pytest.raises(ValueError):
        HttpClient("not-a-url", qps=1)


def test_non_positive_qps_rejected():
    with pytest.raises(ValueError):
        HttpClient("https://example.com/", qps=0)


def test_user_agent_from_env(server, monkeypatch):
    monkeypatch.setenv("POLITE_HTTP_USER_AGENT", "my-agent/1.0")
    received = {}

    def handler(h):
        received["ua"] = h.headers.get("User-Agent")
        _respond(h, 200, "ok")

    server.routes["/ua"] = handler
    client = _client(server)
    client.fetch("ua")
    assert received["ua"] == "my-agent/1.0"


def test_referer_header_sent(server):
    received = {}

    def handler(h):
        received["referer"] = h.headers.get("Referer")
        _respond(h, 200, "ok")

    server.routes["/ref"] = handler
    client = _client(server, referer="https://example.com/source")
    client.fetch("ref")
    assert received["referer"] == "https://example.com/source"


def test_compute_backoff_respects_max(server):
    client = _client(server, backoff_base=10.0, backoff_max=15.0, jitter=0.0)
    assert client._compute_backoff(0) == 10.0
    assert client._compute_backoff(5) == 15.0  # capped


def test_compute_backoff_honors_retry_after(server):
    client = _client(server, backoff_base=1.0, backoff_max=100.0, jitter=0.0)
    assert client._compute_backoff(0, retry_after=42.0) == 42.0


class _Headers(dict):
    pass


def test_parse_retry_after_seconds():
    assert _parse_retry_after(_Headers({"Retry-After": "30"})) == 30.0


def test_parse_retry_after_absent():
    assert _parse_retry_after(_Headers()) is None


def test_parse_throttle_control():
    headers = _Headers({"X-Throttling-Control": "Request Count status: Red (82%)"})
    assert _parse_throttle_control(headers) == 5.0


def test_parse_throttle_control_absent():
    assert _parse_throttle_control(_Headers()) == 0.0


def test_rate_limiter_lock_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("POLITE_HTTP_LOCK_DIR", str(tmp_path))
    limiter = _RateLimiter("example.com", qps=1000)
    limiter.wait()
    assert any(tmp_path.iterdir())


def test_rate_limiter_shares_state_across_instances(tmp_path, monkeypatch):
    # Two limiters for the same host (as two processes would have) must
    # coordinate through the shared lock file: the second call sees the first
    # one's timestamp and waits out the interval.  Exercises the real
    # file-locking path (fcntl on POSIX, msvcrt on Windows).
    monkeypatch.setenv("POLITE_HTTP_LOCK_DIR", str(tmp_path))
    qps = 20.0  # 50ms minimum interval.
    first = _RateLimiter("shared.example.com", qps=qps)
    second = _RateLimiter("shared.example.com", qps=qps)

    first.wait()
    start = time.monotonic()
    second.wait()
    elapsed = time.monotonic() - start

    # Allow generous slack for slow CI, but require a real, non-trivial delay.
    assert elapsed >= (1.0 / qps) * 0.5


def test_rate_limiter_rejects_non_positive_qps():
    with pytest.raises(ValueError):
        _RateLimiter("example.com", qps=0)
