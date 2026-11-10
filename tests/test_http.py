"""TASK-002 验收：限速、重试、Cookie 隔离、弹幕解压。全部使用 MockTransport，不联网。"""

from __future__ import annotations

import zlib
from typing import Any

import httpx
import pytest

from bilitube.http import BiliApiError, BiliClient


def raw_deflate(data: bytes) -> bytes:
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
    return compressor.compress(data) + compressor.flush()


def make_client(handler, **kwargs: Any) -> BiliClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    kwargs.setdefault("rate_limit_rps", 0)
    kwargs.setdefault("sleeper", lambda _seconds: None)
    return BiliClient(client=http_client, **kwargs)


def test_video_detail_ok() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 0, "data": {"bvid": "BV1xx", "cid": 42}})

    client = make_client(handler)
    detail = client.video_detail("BV1xx")
    assert detail["bvid"] == "BV1xx"
    assert client.stats["ok"] == 1


def test_retry_on_risk_control() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] <= 2:
            return httpx.Response(200, json={"code": -352, "message": "风控"})
        return httpx.Response(200, json={"code": 0, "data": {"ok": True}})

    client = make_client(handler, max_attempts=3)
    assert client.video_detail("BV1xx")["ok"] is True
    assert calls["n"] == 3
    assert client.stats["risk_control"] == 2


def test_no_retry_on_403() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"code": -403, "message": "无权限"})

    client = make_client(handler, max_attempts=3)
    with pytest.raises(BiliApiError) as excinfo:
        client.video_detail("BV1xx")
    assert excinfo.value.code == -403
    assert excinfo.value.retryable is False
    assert calls["n"] == 1


def test_rate_limit_sleeps_between_requests() -> None:
    waits: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 0, "data": {}})

    client = make_client(
        handler,
        rate_limit_rps=1.5,
        sleeper=waits.append,
        clock=lambda: 100.0,
    )
    client.video_detail("BV1")
    client.video_detail("BV2")
    client.video_detail("BV3")
    assert len(waits) == 2
    assert all(wait >= 0.6 for wait in waits), waits


def test_cookie_only_when_sessdata() -> None:
    seen: list[httpx.Headers] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers)
        return httpx.Response(200, json={"code": 0, "data": {}})

    make_client(handler).video_detail("BV1")
    assert "cookie" not in seen[0]

    make_client(handler, sessdata="token").video_detail("BV2")
    assert "SESSDATA=token" in seen[1]["cookie"]


def test_danmaku_decompress() -> None:
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?><i>'
        '<d p="1,1,25,16777215">第一条弹幕</d>'
        '<d p="2,1,25,16777215">第二条 &amp; 转义</d>'
        "</i>"
    ).encode("utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=raw_deflate(xml))

    client = make_client(handler)
    result = client.danmaku(123)
    assert result == ["第一条弹幕", "第二条 & 转义"]


def test_abort_when_risk_ratio_exceeds_threshold() -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        return httpx.Response(200, json={"code": 0, "data": {}})

    client = make_client(handler)
    client.stats.update({"requests": 40, "risk_control": 5})
    with pytest.raises(BiliApiError) as excinfo:
        client._check_abort()
    assert "超过阈值" in str(excinfo.value)


def test_search_detects_voucher_challenge() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(200, json={"code": 0, "data": {"v_voucher": "x"}})
        return httpx.Response(200, json={"code": 0, "data": {"result": [{"bvid": "BV1"}]}})

    client = make_client(handler, max_attempts=2)
    result = client.search_videos("RAG")
    assert result == [{"bvid": "BV1"}]
    assert client.stats["risk_control"] == 1


def test_search_empty_result_is_valid() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 0, "data": {"result": []}})

    client = make_client(handler)
    assert client.search_videos("不存在的关键词") == []
    assert client.stats["risk_control"] == 0

def test_warmup_sets_device_cookie() -> None:
    """热身取到 buvid 后，后续请求必须带上设备 cookie（搜索接口没它一律 412）。"""
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/x/frontend/finger/spi"):
            return httpx.Response(200, json={"code": 0, "data": {"b_3": "B3", "b_4": "B4"}})
        seen["cookie"] = request.headers.get("cookie", "")
        return httpx.Response(200, json={"code": 0, "data": {"ok": True}})

    client = make_client(handler)
    assert client.warmup() is True
    client.video_detail("BV1xx")
    assert "buvid3=B3" in seen["cookie"]
    assert "buvid4=B4" in seen["cookie"]


def test_warmup_failure_is_not_fatal() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    client = make_client(handler)
    assert client.warmup() is False
    assert "Cookie" not in client.headers()


def test_sessdata_and_buvid_coexist() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/x/frontend/finger/spi"):
            return httpx.Response(200, json={"code": 0, "data": {"b_3": "B3", "b_4": "B4"}})
        return httpx.Response(200, json={"code": 0, "data": {}})

    client = make_client(handler, sessdata="sess-token")
    client.warmup()
    cookie = client.headers()["Cookie"]
    assert "buvid3=B3" in cookie
    assert "SESSDATA=sess-token" in cookie
