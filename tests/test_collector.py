"""TASK-004 验收：分页、去重、断点续采、失败处理。全部离线。"""

from __future__ import annotations

from pathlib import Path

import pytest

from bilitube.collector import (
    collect_search,
    normalize_cover,
    normalize_search_item,
    parse_duration,
    read_keywords,
)
from bilitube.db import connect, get_crawl_state, init_db, table_counts
from bilitube.http import BiliApiError


def item(bvid: str, title: str = "标题") -> dict:
    return {
        "bvid": bvid,
        "aid": 1,
        "title": f'<em class="keyword">{title}</em>',
        "author": "UP",
        "mid": 10,
        "duration": "10:00",
        "pubdate": 1700000000,
        "typename": "科技",
        "play": 100,
        "like": 10,
        "favorites": 5,
        "video_review": 3,
        "review": 2,
    }


class StubClient:
    def __init__(self, pages=None, fail_on=None):
        self.pages = pages or {}
        self.fail_on = fail_on or set()
        self.calls: list[tuple[str, str, int]] = []
        self.stats = {"requests": 0, "risk_control": 0}

    def search_videos(self, keyword, order="stow", page=1, page_size=20):
        self.calls.append((keyword, order, page))
        self.stats["requests"] += 1
        if (keyword, order, page) in self.fail_on:
            raise BiliApiError(-352, "风控", retryable=True)
        return self.pages.get((keyword, order, page), [])


def open_db(tmp_path: Path):
    conn = connect(tmp_path / "bilitube.db")
    init_db(conn)
    return conn


def test_pagination_stops_at_short_page(tmp_path: Path) -> None:
    client = StubClient(
        pages={
            ("大模型", "stow", 1): [item("BV1"), item("BV2")],
            ("大模型", "stow", 2): [item("BV3")],
        }
    )
    conn = open_db(tmp_path)
    report = collect_search(
        client, conn, ["大模型"], orders=("stow",), max_pages=5, page_size=2
    )
    assert report.pages_done == 2
    assert report.pages_failed == 0
    assert report.records_written == 3
    assert report.unique_bvids == 3
    assert client.calls == [("大模型", "stow", 1), ("大模型", "stow", 2)]
    conn.close()


def test_dedupe_across_pages(tmp_path: Path) -> None:
    client = StubClient(
        pages={
            ("Agent", "stow", 1): [item("BV1"), item("BV1")],
            ("Agent", "stow", 2): [item("BV1")],
        }
    )
    conn = open_db(tmp_path)
    report = collect_search(
        client, conn, ["Agent"], orders=("stow",), max_pages=5, page_size=2
    )
    assert table_counts(conn)["raw_videos"] == 1
    assert report.unique_bvids == 1
    conn.close()


def test_resume_skips_done_pages(tmp_path: Path) -> None:
    pages = {
        ("RAG", "stow", 1): [item("BV1"), item("BV2")],
        ("RAG", "stow", 2): [item("BV3")],
    }
    conn = open_db(tmp_path)
    client = StubClient(pages=pages)

    first = collect_search(client, conn, ["RAG"], orders=("stow",), max_pages=5, page_size=2)
    assert first.pages_done == 2

    second = collect_search(client, conn, ["RAG"], orders=("stow",), max_pages=5, page_size=2)
    assert second.pages_done == 0
    assert second.pages_skipped == 2
    assert table_counts(conn)["raw_videos"] == 3
    conn.close()


def test_fresh_ignores_crawl_state(tmp_path: Path) -> None:
    """周更增量靠 --fresh 重抓：断点状态不能把已标记的页永久跳过。"""
    pages = {
        ("RAG", "pubdate", 1): [item("BV1"), item("BV2")],
        ("RAG", "pubdate", 2): [item("BV3")],
    }
    conn = open_db(tmp_path)
    client = StubClient(pages=pages)

    first = collect_search(
        client, conn, ["RAG"], orders=("pubdate",), max_pages=5, page_size=2
    )
    assert first.pages_done == 2

    # 不带 fresh：全部跳过
    cached = collect_search(
        client, conn, ["RAG"], orders=("pubdate",), max_pages=5, page_size=2
    )
    assert cached.pages_done == 0
    assert cached.pages_skipped == 2

    # 带 fresh：重新抓，但仍幂等（还是 3 条）
    fresh = collect_search(
        client, conn, ["RAG"], orders=("pubdate",), max_pages=5, page_size=2, fresh=True
    )
    assert fresh.pages_done == 2
    assert fresh.pages_skipped == 0
    assert table_counts(conn)["raw_videos"] == 3
    conn.close()


def test_failed_page_is_recorded_and_breaks(tmp_path: Path) -> None:
    client = StubClient(
        pages={("LoRA", "stow", 2): [item("BV9")]},
        fail_on={("LoRA", "stow", 1)},
    )
    conn = open_db(tmp_path)
    report = collect_search(
        client, conn, ["LoRA"], orders=("stow",), max_pages=5, page_size=2
    )
    assert report.pages_failed == 1
    assert report.pages_done == 0
    assert report.failed_pages[0]["page"] == 1
    assert get_crawl_state(conn, "search:LoRA:stow:1") == "failed"
    assert len(client.calls) == 1
    conn.close()


def test_report_file_written(tmp_path: Path) -> None:
    client = StubClient(pages={("SFT", "stow", 1): [item("BV1")]})
    conn = open_db(tmp_path)
    report_dir = tmp_path / "reports"
    collect_search(
        client,
        conn,
        ["SFT"],
        orders=("stow",),
        max_pages=1,
        page_size=20,
        report_dir=report_dir,
    )
    files = list(report_dir.glob("collect-search-*.json"))
    assert len(files) == 1
    assert '"unique_bvids": 1' in files[0].read_text(encoding="utf-8")
    conn.close()


@pytest.mark.parametrize(
    ("text", "expected"),
    [("931:47", 55907), ("1:02:03", 3723), ("45", 45), ("", None), (None, None)],
)
def test_parse_duration(text, expected) -> None:
    assert parse_duration(text) == expected


def test_normalize_strips_html_tags() -> None:
    row = normalize_search_item(item("BV1", "大模型教程"))
    assert row["title"] == "大模型教程"
    assert row["duration"] == 600
    assert row["source"] == "search"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("//i0.hdslb.com/a.jpg", "https://i0.hdslb.com/a.jpg"),
        ("http://i1.hdslb.com/b.jpg", "https://i1.hdslb.com/b.jpg"),
        ("https://i2.hdslb.com/c.jpg", "https://i2.hdslb.com/c.jpg"),
        ("", None),
        (None, None),
    ],
)
def test_normalize_cover(raw, expected) -> None:
    assert normalize_cover(raw) == expected


def test_read_keywords_ignores_comments(tmp_path: Path) -> None:
    path = tmp_path / "keywords.txt"
    path.write_text("# 注释\n大模型\n\nRAG\n", encoding="utf-8")
    assert read_keywords(path) == ["大模型", "RAG"]
