"""TASK-008 验收：弹幕入库、去重、断点、失败标记。全部离线。"""

from __future__ import annotations

from pathlib import Path

from bilitube.collector import collect_danmaku
from bilitube.db import connect, get_crawl_state, init_db
from bilitube.http import BiliApiError


class StubClient:
    def __init__(self, mapping=None, fail_on=None):
        self.mapping = mapping or {}
        self.fail_on = fail_on or set()
        self.calls: list[int] = []
        self.stats = {"requests": 0, "risk_control": 0}

    def danmaku(self, cid: int):
        self.calls.append(cid)
        if cid in self.fail_on:
            raise BiliApiError(-404, "不存在")
        return self.mapping.get(cid, [])


def open_db(tmp_path: Path):
    conn = connect(tmp_path / "bilitube.db")
    init_db(conn)
    return conn


def seed(conn, rows):
    conn.executemany(
        "INSERT INTO raw_videos (bvid, title, cid, view, collected_at) VALUES (?, ?, ?, ?, ?)",
        [(row["bvid"], row.get("title", "标题"), row["cid"], row.get("view", 1), "") for row in rows],
    )
    conn.executemany(
        "INSERT INTO videos (bvid, status, updated_at) VALUES (?, 'passed', '')",
        [(row["bvid"],) for row in rows],
    )
    conn.commit()


def test_danmaku_inserts(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    seed(conn, [{"bvid": "BV1", "cid": 101}, {"bvid": "BV2", "cid": 202}])
    client = StubClient({101: ["a", "b"], 202: ["c"]})

    report = collect_danmaku(client, conn)
    assert report.targets == 2
    assert report.done == 2
    assert report.inserted == 3
    assert conn.execute("SELECT COUNT(*) FROM raw_danmaku").fetchone()[0] == 3
    conn.close()


def test_danmaku_dedupes(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    seed(conn, [{"bvid": "BV1", "cid": 101}])
    client = StubClient({101: ["重复", "重复", "唯一", ""]})

    report = collect_danmaku(client, conn)
    assert report.inserted == 2
    assert conn.execute("SELECT COUNT(*) FROM raw_danmaku").fetchone()[0] == 2
    conn.close()


def test_resume_skips_done(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    seed(conn, [{"bvid": "BV1", "cid": 101}])
    client = StubClient({101: ["a"]})

    collect_danmaku(client, conn)
    calls_after_first = len(client.calls)
    second = collect_danmaku(client, conn)
    assert second.targets == 0
    assert second.done == 0
    assert len(client.calls) == calls_after_first
    assert get_crawl_state(conn, "danmaku:BV1") == "done"
    conn.close()


def test_failure_marks_state(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    seed(conn, [{"bvid": "BV1", "cid": 101}, {"bvid": "BV2", "cid": 202}])
    client = StubClient({202: ["x"]}, fail_on={101})

    report = collect_danmaku(client, conn)
    assert report.failed == 1
    assert report.done == 1
    assert get_crawl_state(conn, "danmaku:BV1") == "failed"
    conn.close()


def test_limit(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    seed(conn, [{"bvid": f"BV{i}", "cid": i, "view": 100 - i} for i in range(1, 4)])
    client = StubClient({1: ["a"], 2: ["b"], 3: ["c"]})

    report = collect_danmaku(client, conn, limit=2)
    assert report.targets == 2
    assert report.done == 2
    conn.close()
