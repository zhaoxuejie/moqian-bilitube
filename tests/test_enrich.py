"""TASK-005 验收：详情补齐、UP 粉丝去重、失败标记、跳过已完成。全部离线。"""

from __future__ import annotations

from pathlib import Path

from bilitube.collector import collect_enrich
from bilitube.db import (
    connect,
    enrich_stats,
    get_up_fans,
    get_video,
    init_db,
    upsert_videos,
)
from bilitube.http import BiliApiError


def detail(bvid: str, mid: int = 100) -> dict:
    return {
        "bvid": bvid,
        "cid": 999,
        "tname_v2": "科技",
        "videos": 1,
        "desc": "视频简介",
        "owner": {"mid": mid, "name": "某 UP"},
        "stat": {"view": 12345, "like": 100, "coin": 50, "favorite": 200, "danmaku": 30, "reply": 20},
    }


class StubClient:
    def __init__(self, details=None, fail_on=None, fans=None):
        self.details = details or {}
        self.fail_on = fail_on or set()
        self.fans = fans or {}
        self.calls: list[tuple[str, object]] = []
        self.stats = {"requests": 0, "risk_control": 0}

    def video_detail(self, bvid: str) -> dict:
        self.calls.append(("detail", bvid))
        if bvid in self.fail_on:
            raise BiliApiError(-404, "不存在")
        return self.details[bvid]

    def up_fans(self, mid: int) -> int:
        self.calls.append(("fans", mid))
        return self.fans.get(mid, 0)


def seed(conn, rows):
    upsert_videos(conn, [{"bvid": b["bvid"], "view": b.get("view", 1)} for b in rows])


def open_db(tmp_path: Path):
    conn = connect(tmp_path / "bilitube.db")
    init_db(conn)
    return conn


def test_enrich_updates_fields(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    seed(conn, [{"bvid": "BV1", "view": 100}])
    client = StubClient(details={"BV1": detail("BV1")}, fans={100: 5000})

    report = collect_enrich(client, conn)
    assert report.done == 1
    assert report.fans_fetched == 1

    row = get_video(conn, "BV1")
    assert row["cid"] == 999
    assert row["coin"] == 50
    assert row["description"] == "视频简介"
    assert row["enrich_status"] == "done"
    assert '"bvid": "BV1"' in row["raw_json"]
    assert get_up_fans(conn, 100) == 5000
    conn.close()


def test_second_run_skips_done(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    seed(conn, [{"bvid": "BV1", "view": 100}])
    client = StubClient(details={"BV1": detail("BV1")})

    collect_enrich(client, conn)
    calls_after_first = len(client.calls)

    second = collect_enrich(client, conn)
    assert second.candidates == 0
    assert second.done == 0
    assert len(client.calls) == calls_after_first
    conn.close()


def test_fans_deduped_by_mid(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    seed(conn, [{"bvid": "BV1", "view": 100}, {"bvid": "BV2", "view": 50}])
    client = StubClient(
        details={"BV1": detail("BV1", mid=7), "BV2": detail("BV2", mid=7)},
        fans={7: 888},
    )

    collect_enrich(client, conn)
    fans_calls = [c for c in client.calls if c[0] == "fans"]
    assert len(fans_calls) == 1
    assert get_up_fans(conn, 7) == 888
    conn.close()


def test_failure_marks_status(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    seed(conn, [{"bvid": "BV1", "view": 100}, {"bvid": "BV2", "view": 50}])
    client = StubClient(
        details={"BV2": detail("BV2")},
        fail_on={"BV1"},
    )

    report = collect_enrich(client, conn)
    assert report.failed == 1
    assert report.done == 1
    assert enrich_stats(conn)["failed"] == 1
    conn.close()


def test_abort_after_ten_consecutive_retryable_errors(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    seed(conn, [{"bvid": f"BV{i}", "view": 100 - i} for i in range(1, 13)])

    class AbortClient(StubClient):
        def video_detail(self, bvid: str) -> dict:
            self.calls.append(("detail", bvid))
            raise BiliApiError(-352, "风控", retryable=True)

    client = AbortClient()
    report = collect_enrich(client, conn)
    assert report.aborted is True
    assert len(client.calls) == 10
    conn.close()


def test_limit(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    seed(conn, [{"bvid": f"BV{i}", "view": 100 - i} for i in range(1, 4)])
    details = {f"BV{i}": detail(f"BV{i}") for i in range(1, 4)}
    client = StubClient(details=details)

    report = collect_enrich(client, conn, limit=1)
    assert report.candidates == 1
    assert report.done == 1
    assert len([c for c in client.calls if c[0] == "detail"]) == 1
    conn.close()
