"""TASK-006 验收：各条过滤规则、UP 配额、幂等与报告。全部离线。"""

from __future__ import annotations

from pathlib import Path

from bilitube.db import connect, init_db, upsert_videos
from bilitube.filter import (
    STATUS_PASSED,
    STATUS_REJECTED,
    STATUS_REVIEW,
    FilterReport,
    apply_filter,
    decide,
    summarize,
)

RULES = {
    "ai_terms": ["大模型", "AI"],
    "bait_terms": ["最全"],
    "collection_terms": ["合集"],
    "allowed_tnames": ["计算机技术"],
    "min_duration_seconds": 180,
    "max_videos_per_up": 2,
}


def video(**kwargs):
    base = {
        "title": "大模型入门教程",
        "duration": 600,
        "tname": "计算机技术",
        "view": 100,
        "mid": 1,
    }
    base.update(kwargs)
    return base


def test_pass() -> None:
    assert decide(video(), RULES) == (STATUS_PASSED, "")


def test_too_short() -> None:
    assert decide(video(duration=60), RULES) == (STATUS_REJECTED, "duration_too_short")


def test_tname_not_allowed() -> None:
    assert decide(video(tname="单机游戏"), RULES) == (STATUS_REJECTED, "tname:单机游戏")


def test_not_ai_related() -> None:
    assert decide(video(title="周末去哪儿玩"), RULES)[1] == "not_ai_related"


def test_clickbait() -> None:
    assert decide(video(title="全网最全的大模型教程"), RULES)[1] == "clickbait:最全"


def test_long_collection_goes_to_review() -> None:
    status, reason = decide(video(title="大模型合集", duration=4 * 3600), RULES)
    assert status == STATUS_REVIEW
    assert reason.startswith("long_collection")


def test_short_collection_is_not_reviewed() -> None:
    assert decide(video(title="大模型合集", duration=600), RULES)[0] == STATUS_PASSED


def open_db(tmp_path: Path):
    conn = connect(tmp_path / "bilitube.db")
    init_db(conn)
    return conn


def test_up_quota(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    rows = [
        {"bvid": "BV1", "title": "大模型 A", "duration": 600, "tname": "计算机技术", "view": 300, "up_mid": 9},
        {"bvid": "BV2", "title": "大模型 B", "duration": 600, "tname": "计算机技术", "view": 200, "up_mid": 9},
        {"bvid": "BV3", "title": "大模型 C", "duration": 600, "tname": "计算机技术", "view": 100, "up_mid": 9},
    ]
    upsert_videos(conn, rows)

    report = apply_filter(conn, RULES)
    assert report.passed == 2
    assert report.rejected == 1
    assert report.reasons.get("up_quota") == 1

    statuses = dict(conn.execute("SELECT bvid, status FROM videos").fetchall())
    assert statuses["BV1"] == "passed"
    assert statuses["BV2"] == "passed"
    assert statuses["BV3"] == "rejected"
    conn.close()


def test_filter_is_idempotent(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    upsert_videos(
        conn,
        [
            {"bvid": "BV1", "title": "大模型 A", "duration": 600, "tname": "计算机技术", "view": 1},
            {"bvid": "BV2", "title": "旅游 vlog", "duration": 600, "tname": "日常", "view": 1},
        ],
    )
    first = apply_filter(conn, RULES)
    second = apply_filter(conn, RULES)
    assert first.as_dict() == second.as_dict()
    assert conn.execute("SELECT COUNT(*) FROM videos").fetchone()[0] == 2
    conn.close()


def test_summarize_contains_counts() -> None:
    text = summarize(FilterReport(total=10, passed=6, review=1, rejected=3, reasons={"up_quota": 2}))
    assert "通过 6" in text
    assert "up_quota" in text
