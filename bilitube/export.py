"""把 SQLite 里的最终结果导出成站点消费的 JSON。"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ExportReport:
    videos: int = 0
    with_cards: int = 0
    topics: int = 0
    out_dir: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "videos": self.videos,
            "with_cards": self.with_cards,
            "topics": self.topics,
            "out_dir": self.out_dir,
        }


def _count(conn: Any, table: str) -> int:
    """安全计数：表不存在时返回 0（导出不应因子表缺失而失败）。"""
    try:
        row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
    except Exception:
        return 0
    return int(row[0]) if row else 0


def _parse_flags(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        return [str(item) for item in value] if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []


def export_site(conn: Any, out_dir: Path) -> ExportReport:
    rows = conn.execute(
        "SELECT r.bvid, r.title, r.up_name, r.up_mid, r.duration, r.pubdate, "
        "COALESCE(NULLIF(r.tname_v2, ''), r.tname, '') AS tname, r.cover, "
        "r.view, r.favorite, r.coin, r.danmaku, r.reply, "
        "s.machine, s.content, s.total, s.flags, c.payload "
        "FROM raw_videos r "
        "JOIN videos v ON v.bvid = r.bvid AND v.status = 'passed' "
        "JOIN scores s ON s.bvid = r.bvid "
        "LEFT JOIN cards c ON c.bvid = r.bvid "
        "ORDER BY s.total DESC"
    ).fetchall()

    videos: list[dict[str, Any]] = []
    topic_counter: Counter[str] = Counter()
    with_cards = 0

    for row in rows:
        card = None
        if row["payload"]:
            try:
                card = json.loads(row["payload"])
                with_cards += 1
            except json.JSONDecodeError:
                card = None
        if card:
            for topic in card.get("topics") or []:
                topic_counter[str(topic)] += 1

        videos.append(
            {
                "bvid": row["bvid"],
                "title": row["title"],
                "up": row["up_name"],
                "mid": row["up_mid"],
                "duration": row["duration"],
                "pubdate": row["pubdate"],
                "tname": row["tname"],
                "cover": row["cover"],
                "view": row["view"],
                "favorite": row["favorite"],
                "coin": row["coin"],
                "danmaku": row["danmaku"],
                "reply": row["reply"],
                "scores": {
                    "machine": row["machine"],
                    "content": row["content"],
                    "total": row["total"],
                },
                "flags": _parse_flags(row["flags"]),
                "card": card,
            }
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "videos.json").write_text(
        json.dumps(videos, ensure_ascii=False), encoding="utf-8"
    )

    topics = [
        {"name": name, "count": count}
        for name, count in topic_counter.most_common(80)
        if count >= 3
    ]
    (out_dir / "topics.json").write_text(
        json.dumps(topics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "meta.json").write_text(
        json.dumps(
            {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "videos": len(videos),
                "with_cards": with_cards,
                "topics": len(topics),
                "candidates": _count(conn, "raw_videos"),
                "danmaku_rows": _count(conn, "raw_danmaku"),
                "covers": sum(1 for item in videos if item["cover"]),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return ExportReport(
        videos=len(videos),
        with_cards=with_cards,
        topics=len(topics),
        out_dir=str(out_dir),
    )


def summarize(report: ExportReport) -> str:
    return (
        f"导出 {report.videos} 条视频（含卡片 {report.with_cards}）、"
        f"{report.topics} 个主题 → {report.out_dir}"
    )
