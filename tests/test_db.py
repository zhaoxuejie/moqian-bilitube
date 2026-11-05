"""TASK-003 验收：建表幂等、upsert 幂等、采集状态流转。全部离线。"""

from __future__ import annotations

from pathlib import Path

from bilitube.db import (
    SCHEMA_VERSION,
    STATE_DONE,
    STATE_FAILED,
    STATE_PENDING,
    connect,
    done_keys,
    get_crawl_state,
    get_video,
    init_db,
    set_crawl_state,
    table_counts,
    upsert_videos,
)


def open_db(tmp_path: Path):
    conn = connect(tmp_path / "data" / "bilitube.db")
    init_db(conn)
    return conn


def test_init_is_idempotent(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    init_db(conn)
    versions = conn.execute("SELECT version FROM schema_version").fetchall()
    assert len(versions) == SCHEMA_VERSION
    assert max(row["version"] for row in versions) == SCHEMA_VERSION
    tables = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    assert {"raw_videos", "raw_comments", "raw_ups", "crawl_state", "scores", "cards"} <= tables
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(raw_videos)").fetchall()}
    assert {"cid", "coin", "enrich_status", "raw_json", "description"} <= columns
    conn.close()


def test_upsert_is_idempotent(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    record = {"bvid": "BV1xx", "title": "旧标题", "view": 100}
    assert upsert_videos(conn, [record]) == 1
    assert table_counts(conn)["raw_videos"] == 1

    upsert_videos(conn, [{"bvid": "BV1xx", "title": "新标题", "view": 200}])
    assert table_counts(conn)["raw_videos"] == 1
    stored = get_video(conn, "BV1xx")
    assert stored is not None
    assert stored["title"] == "新标题"
    assert stored["view"] == 200
    assert stored["collected_at"]
    conn.close()


def test_crawl_state_transitions(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    key = "search:大模型:stow:1"

    set_crawl_state(conn, key, STATE_PENDING)
    assert get_crawl_state(conn, key) == STATE_PENDING

    set_crawl_state(conn, key, STATE_DONE)
    assert get_crawl_state(conn, key) == STATE_DONE
    assert key in done_keys(conn)

    set_crawl_state(conn, key, STATE_FAILED, error="timeout")
    row = conn.execute("SELECT attempts, error FROM crawl_state WHERE key = ?", (key,)).fetchone()
    assert row["attempts"] == 3
    assert row["error"] == "timeout"
    conn.close()


def test_db_path_is_configurable(tmp_path: Path) -> None:
    path = tmp_path / "custom" / "x.db"
    conn = connect(path)
    init_db(conn)
    assert path.exists()
    conn.close()


def test_upsert_does_not_wipe_enriched_fields(tmp_path: Path) -> None:
    """重跑搜索采集时，不能把 enrich 补出来的字段冲成 NULL。"""
    conn = open_db(tmp_path)
    upsert_videos(conn, [{"bvid": "BV1", "title": "旧", "view": 100}])
    conn.execute("UPDATE raw_videos SET coin = 42, cid = 7 WHERE bvid = 'BV1'")
    conn.commit()

    upsert_videos(conn, [{"bvid": "BV1", "title": "新", "view": 200}])
    row = get_video(conn, "BV1")
    assert row["coin"] == 42
    assert row["cid"] == 7
    assert row["view"] == 200
    assert row["title"] == "新"
    conn.close()
