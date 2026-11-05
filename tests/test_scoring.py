"""TASK-007 验收：分位计算、分组退化、分数边界与幂等。全部离线。"""

from __future__ import annotations

from pathlib import Path

from bilitube.db import connect, init_db, upsert_videos
from bilitube.scoring import (
    MIN_GROUP_SIZE,
    compute_metrics,
    duration_bucket,
    percentiles,
    score_all,
)


def open_db(tmp_path: Path):
    conn = connect(tmp_path / "bilitube.db")
    init_db(conn)
    return conn


def seed(conn, records):
    upsert_videos(conn, records)
    conn.executemany(
        "INSERT INTO videos (bvid, status, updated_at) VALUES (?, 'passed', '')",
        [(record["bvid"],) for record in records],
    )
    conn.commit()


def test_duration_bucket() -> None:
    assert duration_bucket(60) == "<10min"
    assert duration_bucket(900) == "10-30min"
    assert duration_bucket(3600) == "30-90min"
    assert duration_bucket(7200) == ">90min"
    assert duration_bucket(None) == "<10min"


def test_percentiles() -> None:
    assert percentiles([]) == []
    assert percentiles([5]) == [50.0]
    assert percentiles([1, 2, 3]) == [0.0, 50.0, 100.0]
    assert percentiles([3, 1, 2]) == [100.0, 0.0, 50.0]


def test_compute_metrics() -> None:
    metrics = compute_metrics(
        {"view": 1000, "favorite": 50, "coin": 10, "like_count": 20, "danmaku": 5, "reply": 5}
    )
    assert metrics["fav_rate"] == 0.05
    assert metrics["coin_rate"] == 0.01
    assert metrics["talk_rate"] == 0.01
    assert metrics["log_view"] > 0


def test_higher_fav_gets_higher_score(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    records = []
    for index in range(MIN_GROUP_SIZE):
        records.append(
            {
                "bvid": f"BV{index}",
                "title": "大模型教程",
                "duration": 900,
                "tname": "计算机技术",
                "view": 10000,
                "favorite": 100 + index * 10,
                "coin": 10,
                "like_count": 100,
                "danmaku": 5,
                "reply": 5,
            }
        )
    seed(conn, records)

    report = score_all(conn)
    assert report.scored == MIN_GROUP_SIZE

    scores = dict(conn.execute("SELECT bvid, total FROM scores").fetchall())
    assert scores["BV29"] > scores["BV0"]
    assert all(0 <= value <= 100 for value in scores.values())
    conn.close()


def test_low_sample_falls_back_to_global(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    seed(
        conn,
        [
            {"bvid": "BV1", "title": "大模型", "duration": 900, "tname": "小众分区", "view": 100, "favorite": 5},
            {"bvid": "BV2", "title": "大模型", "duration": 900, "tname": "计算机技术", "view": 100, "favorite": 9},
        ],
    )
    report = score_all(conn)
    assert report.low_sample == 2
    flags = conn.execute("SELECT flags FROM scores").fetchall()
    assert all("low_sample" in row["flags"] for row in flags)
    conn.close()


def test_score_is_idempotent(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    seed(
        conn,
        [
            {"bvid": "BV1", "title": "大模型", "duration": 900, "tname": "计算机技术", "view": 100, "favorite": 5},
        ],
    )
    first = score_all(conn)
    second = score_all(conn)
    assert first.as_dict()["scored"] == second.as_dict()["scored"]
    assert conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0] == 1
    conn.close()


def test_rescore_keeps_content_score(tmp_path: Path) -> None:
    """重跑 score 不能把 card 阶段算出的内容分抹掉（曾经会）。"""
    conn = open_db(tmp_path)
    records = [
        {
            "bvid": f"BV{index}",
            "title": "大模型教程",
            "duration": 900,
            "tname": "计算机技术",
            "view": 10000,
            "favorite": 100 + index * 10,
            "coin": 10,
            "like_count": 100,
            "danmaku": 5,
            "reply": 5,
        }
        for index in range(MIN_GROUP_SIZE)
    ]
    seed(conn, records)
    score_all(conn)

    # 模拟 card 阶段写入内容分
    conn.execute("UPDATE scores SET content = 90, total = 0.6 * machine + 0.4 * 90")
    conn.commit()
    before = dict(conn.execute("SELECT bvid, total FROM scores").fetchall())

    score_all(conn)

    after = {
        row["bvid"]: (row["content"], row["total"])
        for row in conn.execute("SELECT bvid, content, total FROM scores")
    }
    assert all(content == 90 for content, _ in after.values())
    for bvid, (_, total) in after.items():
        assert abs(total - before[bvid]) < 0.01
    conn.close()

def test_preset_with_subset_of_metrics(tmp_path: Path) -> None:
    """配方只声明部分信号（example 只用了三个）时，打分不应报错。"""
    from bilitube.preset import load_preset

    preset = load_preset(Path(__file__).resolve().parents[1] / "presets" / "example")
    conn = open_db(tmp_path)
    records = [
        {
            "bvid": f"BV{index}",
            "title": "示例视频",
            "duration": 900,
            "tname": "计算机技术",
            "view": 10000,
            "favorite": 100 + index * 10,
            "coin": 10,
            "like_count": 100,
        }
        for index in range(MIN_GROUP_SIZE)
    ]
    seed(conn, records)

    report = score_all(conn, preset)
    assert report.scored == MIN_GROUP_SIZE
    scores = dict(conn.execute("SELECT bvid, total FROM scores").fetchall())
    assert scores["BV29"] > scores["BV0"]
    conn.close()