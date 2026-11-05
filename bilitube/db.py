"""SQLite 数据层：建表、迁移、幂等 upsert、采集状态。

设计要点：
- 以 BV 号为主键做幂等写入，重复采集不会产生重复行
- 迁移按版本号顺序执行，记录在 schema_version 表
- 开启 WAL 与外键，兼顾断点续采与并发读
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 4
STATE_PENDING = "pending"
STATE_DONE = "done"
STATE_FAILED = "failed"

_MIGRATION_V1 = """
CREATE TABLE IF NOT EXISTS raw_videos (
    bvid         TEXT PRIMARY KEY,
    aid          INTEGER,
    title        TEXT,
    up_mid       INTEGER,
    up_name      TEXT,
    duration     INTEGER,
    pubdate      INTEGER,
    tname        TEXT,
    view         INTEGER,
    like_count   INTEGER,
    coin         INTEGER,
    favorite     INTEGER,
    danmaku      INTEGER,
    reply        INTEGER,
    source       TEXT,
    raw_json     TEXT,
    collected_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_topics (
    keyword    TEXT NOT NULL,
    order_type TEXT NOT NULL,
    page       INTEGER NOT NULL,
    total      INTEGER,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (keyword, order_type, page)
);

CREATE TABLE IF NOT EXISTS raw_comments (
    bvid       TEXT NOT NULL,
    rpid       TEXT NOT NULL,
    content    TEXT,
    like_count INTEGER,
    created    INTEGER,
    PRIMARY KEY (bvid, rpid)
);

CREATE TABLE IF NOT EXISTS raw_danmaku (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    bvid       TEXT NOT NULL,
    content    TEXT NOT NULL,
    UNIQUE (bvid, content)
);

CREATE TABLE IF NOT EXISTS raw_subtitles (
    bvid       TEXT NOT NULL,
    lang       TEXT NOT NULL,
    content    TEXT,
    collected_at TEXT NOT NULL,
    PRIMARY KEY (bvid, lang)
);

CREATE TABLE IF NOT EXISTS videos (
    bvid       TEXT PRIMARY KEY,
    status     TEXT NOT NULL DEFAULT 'candidate',
    series_id  TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scores (
    bvid       TEXT PRIMARY KEY,
    content    REAL,
    machine    REAL,
    total      REAL,
    flags      TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cards (
    bvid       TEXT PRIMARY KEY,
    payload    TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crawl_state (
    key        TEXT PRIMARY KEY,
    status     TEXT NOT NULL CHECK (status IN ('pending', 'done', 'failed')),
    attempts   INTEGER NOT NULL DEFAULT 0,
    error      TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_raw_videos_pubdate ON raw_videos (pubdate);
CREATE INDEX IF NOT EXISTS idx_raw_videos_source ON raw_videos (source);
CREATE INDEX IF NOT EXISTS idx_scores_total ON scores (total);
"""

_MIGRATION_V2 = """
ALTER TABLE raw_videos ADD COLUMN cid INTEGER;
ALTER TABLE raw_videos ADD COLUMN tname_v2 TEXT;
ALTER TABLE raw_videos ADD COLUMN videos INTEGER;
ALTER TABLE raw_videos ADD COLUMN description TEXT;
ALTER TABLE raw_videos ADD COLUMN owner_mid INTEGER;
ALTER TABLE raw_videos ADD COLUMN enrich_status TEXT NOT NULL DEFAULT 'pending';
ALTER TABLE raw_videos ADD COLUMN enrich_error TEXT NOT NULL DEFAULT '';
ALTER TABLE raw_videos ADD COLUMN enriched_at TEXT;

CREATE TABLE IF NOT EXISTS raw_ups (
    mid        INTEGER PRIMARY KEY,
    name       TEXT,
    fans       INTEGER,
    fetched_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_raw_videos_enrich ON raw_videos (enrich_status);
"""

_MIGRATION_V3 = """
ALTER TABLE videos ADD COLUMN reject_reason TEXT NOT NULL DEFAULT '';
"""

_MIGRATION_V4 = """
ALTER TABLE raw_videos ADD COLUMN cover TEXT;
UPDATE raw_videos
   SET cover = json_extract(raw_json, '$.pic')
 WHERE cover IS NULL AND raw_json IS NOT NULL;
"""

MIGRATIONS: list[str] = [_MIGRATION_V1, _MIGRATION_V2, _MIGRATION_V3, _MIGRATION_V4]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(db_path: Path | str) -> sqlite3.Connection:
    """打开数据库连接，并确保父目录存在。"""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """按版本顺序执行迁移；可重复调用。"""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version ("
        "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    row = conn.execute("SELECT COALESCE(MAX(version), 0) AS v FROM schema_version").fetchone()
    current = int(row["v"])
    for version, migration in enumerate(MIGRATIONS, start=1):
        if version <= current:
            continue
        conn.executescript(migration)
        conn.execute(
            "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
            (version, _now()),
        )
        conn.commit()


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    """返回各业务表的行数，便于观测与测试断言。"""
    tables = (
        "raw_videos",
        "raw_topics",
        "raw_comments",
        "raw_danmaku",
        "raw_subtitles",
        "videos",
        "scores",
        "cards",
        "crawl_state",
    )
    return {
        table: int(conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"])
        for table in tables
    }


_VIDEO_COLUMNS = (
    "bvid",
    "aid",
    "title",
    "up_mid",
    "up_name",
    "duration",
    "pubdate",
    "tname",
    "view",
    "like_count",
    "coin",
    "favorite",
    "danmaku",
    "reply",
    "source",
    "raw_json",
    "cover",
)


def upsert_videos(conn: sqlite3.Connection, records: Iterable[dict[str, Any]]) -> int:
    """幂等写入视频；返回写入条数（含更新）。"""
    placeholders = ", ".join("?" for _ in _VIDEO_COLUMNS)
    assignments = ", ".join(
        f"{col} = COALESCE(excluded.{col}, raw_videos.{col})"
        for col in _VIDEO_COLUMNS
        if col != "bvid"
    )
    sql = (
        f"INSERT INTO raw_videos ({', '.join(_VIDEO_COLUMNS)}, collected_at) "
        f"VALUES ({placeholders}, ?) "
        f"ON CONFLICT(bvid) DO UPDATE SET {assignments}, collected_at = excluded.collected_at"
    )
    now = _now()
    rows = []
    for record in records:
        values = []
        for column in _VIDEO_COLUMNS:
            value = record.get(column)
            if column == "raw_json" and isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            values.append(value)
        values.append(now)
        rows.append(values)
    conn.executemany(sql, rows)
    conn.commit()
    return len(rows)


def get_video(conn: sqlite3.Connection, bvid: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM raw_videos WHERE bvid = ?", (bvid,)).fetchone()
    return dict(row) if row else None


def set_crawl_state(
    conn: sqlite3.Connection,
    key: str,
    status: str,
    *,
    error: str = "",
) -> None:
    """记录采集状态；attempts 在已是 pending 时累加。"""
    if status not in (STATE_PENDING, STATE_DONE, STATE_FAILED):
        raise ValueError(f"非法状态: {status}")
    conn.execute(
        "INSERT INTO crawl_state (key, status, attempts, error, updated_at) "
        "VALUES (?, ?, 1, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET "
        "status = excluded.status, "
        "attempts = crawl_state.attempts + 1, "
        "error = excluded.error, "
        "updated_at = excluded.updated_at",
        (key, status, error, _now()),
    )
    conn.commit()


def get_crawl_state(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT status FROM crawl_state WHERE key = ?", (key,)).fetchone()
    return row["status"] if row else None


def done_keys(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT key FROM crawl_state WHERE status = ?", (STATE_DONE,)).fetchall()
    return {row["key"] for row in rows}


def enrich_stats(conn: sqlite3.Connection) -> dict[str, int]:
    """返回 enrich 各状态的数量。"""
    rows = conn.execute(
        "SELECT enrich_status AS st, COUNT(*) AS c FROM raw_videos GROUP BY enrich_status"
    ).fetchall()
    return {row["st"]: int(row["c"]) for row in rows}


def select_enrich_batch(conn: sqlite3.Connection, limit: int | None = None) -> list[dict[str, Any]]:
    """取还需要补详情的视频，按播放量从高到低。"""
    sql = "SELECT bvid FROM raw_videos WHERE enrich_status != 'done' ORDER BY view DESC"
    params: tuple[Any, ...] = ()
    if limit is not None:
        sql += " LIMIT ?"
        params = (int(limit),)
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def save_detail(conn: sqlite3.Connection, bvid: str, detail: dict[str, Any]) -> None:
    """把详情响应写库：字段写列，整份响应写 raw_json，便于未来从库内复原。"""
    stat = detail.get("stat") or {}
    owner = detail.get("owner") or {}
    conn.execute(
        "UPDATE raw_videos SET cid = ?, tname_v2 = ?, videos = ?, description = ?, "
        "owner_mid = ?, view = ?, like_count = ?, coin = ?, favorite = ?, danmaku = ?, "
        "reply = ?, cover = COALESCE(?, cover), raw_json = ?, "
        "enrich_status = 'done', enrich_error = '', enriched_at = ? "
        "WHERE bvid = ?",
        (
            detail.get("cid"),
            detail.get("tname_v2") or detail.get("tname") or None,
            detail.get("videos"),
            detail.get("desc"),
            owner.get("mid"),
            stat.get("view"),
            stat.get("like"),
            stat.get("coin"),
            stat.get("favorite"),
            stat.get("danmaku"),
            stat.get("reply"),
            detail.get("pic"),
            json.dumps(detail, ensure_ascii=False),
            _now(),
            bvid,
        ),
    )
    conn.commit()


def mark_enrich_failed(conn: sqlite3.Connection, bvid: str, error: str) -> None:
    conn.execute(
        "UPDATE raw_videos SET enrich_status = 'failed', enrich_error = ?, enriched_at = ? "
        "WHERE bvid = ?",
        (error[:500], _now(), bvid),
    )
    conn.commit()


def get_up_fans(conn: sqlite3.Connection, mid: int) -> int | None:
    row = conn.execute("SELECT fans FROM raw_ups WHERE mid = ?", (mid,)).fetchone()
    return None if row is None else row["fans"]


def upsert_up(conn: sqlite3.Connection, mid: int, name: str | None, fans: int | None) -> None:
    conn.execute(
        "INSERT INTO raw_ups (mid, name, fans, fetched_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(mid) DO UPDATE SET name = excluded.name, fans = excluded.fans, "
        "fetched_at = excluded.fetched_at",
        (mid, name, fans, _now()),
    )
    conn.commit()
