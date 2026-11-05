"""TASK-010 数据侧验收：导出 JSON 的结构与排序。离线。"""

from __future__ import annotations

import json
from pathlib import Path

from bilitube.db import connect, init_db
from bilitube.export import export_site


def open_db(tmp_path: Path):
    conn = connect(tmp_path / "bilitube.db")
    init_db(conn)
    return conn


def seed(conn) -> None:
    rows = [("BV1", 90.0), ("BV2", 70.0), ("BV3", 60.0)]
    for index, (bvid, total) in enumerate(rows):
        conn.execute(
            "INSERT INTO raw_videos (bvid, title, up_name, duration, view, favorite, coin, "
            "tname, cover, collected_at) "
            "VALUES (?, ?, 'UP', 900, 1000, 50, 10, '计算机技术', ?, '')",
            (bvid, f"大模型教程 {index}", f"https://i0.hdslb.com/bfs/archive/{bvid}.jpg"),
        )
        conn.execute("INSERT INTO videos (bvid, status, updated_at) VALUES (?, 'passed', '')", (bvid,))
        conn.execute(
            "INSERT INTO scores (bvid, content, machine, total, flags, updated_at) "
            "VALUES (?, 80, 60, ?, '[]', '')",
            (bvid, total),
        )
        conn.execute(
            "INSERT INTO cards (bvid, payload, updated_at) VALUES (?, ?, '')",
            (
                bvid,
                json.dumps(
                    {"summary": "摘要", "topics": ["RAG", "Agent"], "quality": 80},
                    ensure_ascii=False,
                ),
            ),
        )
    conn.commit()


def test_export_writes_files_and_sorts(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    seed(conn)
    out = tmp_path / "out"
    report = export_site(conn, out)

    assert report.videos == 3
    assert report.with_cards == 3
    assert report.topics == 2

    videos = json.loads((out / "videos.json").read_text(encoding="utf-8"))
    assert [item["bvid"] for item in videos] == ["BV1", "BV2", "BV3"]
    assert videos[0]["card"]["topics"] == ["RAG", "Agent"]
    assert videos[0]["scores"]["total"] == 90.0
    assert videos[0]["cover"] == "https://i0.hdslb.com/bfs/archive/BV1.jpg"

    topics = json.loads((out / "topics.json").read_text(encoding="utf-8"))
    assert {item["name"] for item in topics} == {"RAG", "Agent"}

    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["videos"] == 3
    assert meta["covers"] == 3
    conn.close()


def test_export_tolerates_broken_card(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    seed(conn)
    conn.execute("UPDATE cards SET payload = 'not-json' WHERE bvid = 'BV1'")
    conn.commit()

    out = tmp_path / "out"
    report = export_site(conn, out)
    assert report.with_cards == 2
    videos = json.loads((out / "videos.json").read_text(encoding="utf-8"))
    assert videos[0]["card"] is None or videos[0]["bvid"] == "BV2"
    conn.close()
