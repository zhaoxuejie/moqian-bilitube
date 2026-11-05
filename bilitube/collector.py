"""关键词搜索采集：分页、幂等写入、断点续采、采集报告。"""

from __future__ import annotations

import html
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from .db import (
    STATE_DONE,
    STATE_FAILED,
    connect,
    get_crawl_state,
    get_up_fans,
    init_db,
    mark_enrich_failed,
    save_detail,
    select_enrich_batch,
    set_crawl_state,
    upsert_up,
    upsert_videos,
)
from .http import BiliApiError

LOGGER = logging.getLogger("bilitube")

TAG_PATTERN = re.compile(r"<[^>]+>")


def _int(value: Any) -> int | None:
    """把接口里可能是字符串的数值安全转成 int。"""
    if value is None or value == "":
        return None
    try:
        return int(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def parse_duration(text: Any) -> int | None:
    """解析 B 站时长：`931:47` 表示 931 分 47 秒，`1:02:03` 表示 1 小时 2 分 3 秒。"""
    if text is None or text == "":
        return None
    if isinstance(text, (int, float)):
        return int(text)
    parts = [part for part in str(text).strip().split(":")]
    try:
        numbers = [int(part) for part in parts]
    except ValueError:
        return None
    if len(numbers) == 1:
        return numbers[0]
    if len(numbers) == 2:
        return numbers[0] * 60 + numbers[1]
    if len(numbers) == 3:
        return numbers[0] * 3600 + numbers[1] * 60 + numbers[2]
    return None


def normalize_cover(value: Any) -> str | None:
    """把封面地址归一成 https 绝对地址；尺寸参数留给前端按需追加。"""
    if not value:
        return None
    url = str(value).strip()
    if url.startswith("//"):
        url = f"https:{url}"
    elif url.startswith("http://"):
        url = f"https://{url[len('http://') :]}"
    elif not url.startswith("https://"):
        return None
    return url or None


def normalize_search_item(item: dict[str, Any]) -> dict[str, Any]:
    """把搜索接口的条目归一成 raw_videos 的行。"""
    return {
        "bvid": item.get("bvid"),
        "aid": _int(item.get("aid")),
        "title": html.unescape(TAG_PATTERN.sub("", str(item.get("title") or ""))),
        "up_mid": _int(item.get("mid")),
        "up_name": item.get("author"),
        "duration": parse_duration(item.get("duration")),
        "pubdate": _int(item.get("pubdate")),
        "tname": item.get("typename"),
        "view": _int(item.get("play")),
        "like_count": _int(item.get("like")),
        "coin": _int(item.get("coin")),
        "favorite": _int(item.get("favorites")),
        "danmaku": _int(item.get("video_review")),
        "reply": _int(item.get("review")),
        "source": "search",
        "raw_json": item,
        "cover": normalize_cover(item.get("pic")),
    }


@dataclass
class CollectReport:
    keywords: int = 0
    orders: str = ""
    pages_done: int = 0
    pages_skipped: int = 0
    pages_failed: int = 0
    records_written: int = 0
    unique_bvids: int = 0
    risk_ratio: float = 0.0
    failed_pages: list[dict[str, Any]] = field(default_factory=list)
    aborted: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "keywords": self.keywords,
            "orders": self.orders,
            "pages_done": self.pages_done,
            "pages_skipped": self.pages_skipped,
            "pages_failed": self.pages_failed,
            "records_written": self.records_written,
            "unique_bvids": self.unique_bvids,
            "risk_ratio": round(self.risk_ratio, 4),
            "aborted": self.aborted,
            "failed_pages": self.failed_pages,
        }


def _risk_ratio(client: Any) -> float:
    stats = getattr(client, "stats", None) or {}
    requests = stats.get("requests") or 0
    if not requests:
        return 0.0
    return (stats.get("risk_control") or 0) / requests


def _exhausted_page(conn: Any, keyword: str, order: str, page_size: int) -> int | None:
    """返回该关键词+排序已确认"是最后一页"的页码；用于避免每次重跑都多打一页空请求。"""
    row = conn.execute(
        "SELECT page, total FROM raw_topics "
        "WHERE keyword = ? AND order_type = ? ORDER BY page DESC LIMIT 1",
        (keyword, order),
    ).fetchone()
    if row is not None and (row["total"] or 0) < page_size:
        return int(row["page"])
    return None


def collect_search(
    client: Any,
    conn: Any,
    keywords: Sequence[str],
    *,
    orders: Sequence[str] = ("stow", "click"),
    max_pages: int = 50,
    page_size: int = 20,
    report_dir: Path | None = None,
    fresh: bool = False,
) -> CollectReport:
    """按关键词 × 排序方式分页采集，支持断点续采。

    fresh=True 时忽略 crawl_state 与"已到末页"的缓存，强制重抓这几页——
    每周增量采集需要它，否则上周标记过的页会被永久跳过。
    bvid 写入本身幂等，重抓不会产生重复数据。
    """
    report = CollectReport(keywords=len(keywords), orders=",".join(orders))

    for keyword in keywords:
        if report.aborted:
            break
        for order in orders:
            if report.aborted:
                break
            exhausted_at = None if fresh else _exhausted_page(conn, keyword, order, page_size)
            for page in range(1, max_pages + 1):
                if exhausted_at is not None and page > exhausted_at:
                    break
                key = f"search:{keyword}:{order}:{page}"
                if not fresh and get_crawl_state(conn, key) == STATE_DONE:
                    report.pages_skipped += 1
                    continue

                try:
                    items = client.search_videos(
                        keyword, order=order, page=page, page_size=page_size
                    )
                except BiliApiError as exc:
                    set_crawl_state(conn, key, STATE_FAILED, error=str(exc))
                    report.pages_failed += 1
                    report.failed_pages.append(
                        {"keyword": keyword, "order": order, "page": page, "error": str(exc)}
                    )
                    # 风控类失败立即整体中止，避免继续撞墙把 IP 打进更深的冷却
                    report.aborted = exc.retryable
                    break

                records = [
                    normalize_search_item(item)
                    for item in items
                    if isinstance(item, dict) and item.get("bvid")
                ]
                if records:
                    report.records_written += upsert_videos(conn, records)

                conn.execute(
                    "INSERT INTO raw_topics (keyword, order_type, page, total, fetched_at) "
                    "VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT(keyword, order_type, page) DO UPDATE SET "
                    "total = excluded.total, fetched_at = excluded.fetched_at",
                    (keyword, order, page, len(records), datetime.now().isoformat(timespec="seconds")),
                )
                conn.commit()

                set_crawl_state(conn, key, STATE_DONE)
                report.pages_done += 1

                if len(items) < page_size:
                    break

    row = conn.execute("SELECT COUNT(DISTINCT bvid) AS c FROM raw_videos").fetchone()
    report.unique_bvids = int(row["c"])
    report.risk_ratio = _risk_ratio(client)

    if report_dir is not None:
        report_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        (report_dir / f"collect-search-{stamp}.json").write_text(
            json.dumps(report.as_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return report


def read_keywords(path: Path) -> list[str]:
    """读取关键词文件，忽略空行与注释。"""
    words: list[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        words.append(text)
    return words


def open_connection(db_path: Path):
    conn = connect(db_path)
    init_db(conn)
    return conn


def summarize(report: CollectReport) -> str:
    return (
        f"关键词 {report.keywords} 个，订单 [{report.orders}]，"
        f"完成 {report.pages_done} 页，跳过 {report.pages_skipped} 页，"
        f"失败 {report.pages_failed} 页，写入 {report.records_written} 条，"
        f"去重后 {report.unique_bvids} 个视频，风控比例 {report.risk_ratio:.2%}"
    )


@dataclass
class EnrichReport:
    candidates: int = 0
    done: int = 0
    failed: int = 0
    fans_fetched: int = 0
    ups_cached: int = 0
    risk_ratio: float = 0.0
    aborted: bool = False
    failed_items: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidates": self.candidates,
            "done": self.done,
            "failed": self.failed,
            "fans_fetched": self.fans_fetched,
            "ups_cached": self.ups_cached,
            "risk_ratio": round(self.risk_ratio, 4),
            "aborted": self.aborted,
            "failed_items": self.failed_items,
        }


def collect_enrich(
    client: Any,
    conn: Any,
    *,
    limit: int | None = None,
    batch_size: int = 100,
    report_dir: Path | None = None,
) -> EnrichReport:
    """补齐视频详情与 UP 粉丝数；UP 粉丝按 mid 去重缓存。"""
    rows = select_enrich_batch(conn, limit)
    report = EnrichReport(candidates=len(rows))
    consecutive_failures = 0

    for index, row in enumerate(rows, 1):
        bvid = row["bvid"]
        try:
            detail = client.video_detail(bvid)
        except BiliApiError as exc:
            mark_enrich_failed(conn, bvid, str(exc))
            report.failed += 1
            report.failed_items.append({"bvid": bvid, "error": str(exc)})
            consecutive_failures += 1
            # 连续 10 次可重试失败视为风控窗口，整体中止
            if exc.retryable and consecutive_failures >= 10:
                report.aborted = True
                break
            continue

        consecutive_failures = 0
        save_detail(conn, bvid, detail)
        report.done += 1

        owner = detail.get("owner") or {}
        mid = owner.get("mid")
        if mid:
            if get_up_fans(conn, mid) is None:
                try:
                    fans = client.up_fans(mid)
                    upsert_up(conn, mid, owner.get("name"), fans)
                    report.fans_fetched += 1
                except BiliApiError as exc:  # 粉丝数缺失不阻塞主流程
                    LOGGER.warning("粉丝数获取失败 mid=%s: %s", mid, exc)
            else:
                report.ups_cached += 1

        if index % batch_size == 0:
            LOGGER.info(
                "enrich 进度 %d/%d，成功 %d，失败 %d",
                index,
                len(rows),
                report.done,
                report.failed,
            )

    report.risk_ratio = _risk_ratio(client)

    if report_dir is not None:
        report_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        (report_dir / f"enrich-{stamp}.json").write_text(
            json.dumps(report.as_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return report


def summarize_enrich(report: EnrichReport) -> str:
    return (
        f"待补 {report.candidates}，完成 {report.done}，失败 {report.failed}，"
        f"新增粉丝数 {report.fans_fetched}，命中缓存 {report.ups_cached}，"
        f"风控比例 {report.risk_ratio:.2%}"
    )


@dataclass
class DanmakuReport:
    targets: int = 0
    done: int = 0
    failed: int = 0
    inserted: int = 0
    aborted: bool = False
    failed_items: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "targets": self.targets,
            "done": self.done,
            "failed": self.failed,
            "inserted": self.inserted,
            "aborted": self.aborted,
            "failed_items": self.failed_items,
        }


def collect_danmaku(
    client: Any,
    conn: Any,
    *,
    limit: int | None = None,
    batch_size: int = 100,
    report_dir: Path | None = None,
) -> DanmakuReport:
    """只对通过过滤的视频抓弹幕，写入 raw_danmaku 并支持断点续采。"""
    sql = (
        "SELECT r.bvid, r.cid FROM raw_videos r JOIN videos v ON v.bvid = r.bvid "
        "WHERE v.status = 'passed' AND r.cid IS NOT NULL "
        "AND NOT EXISTS ("
        "SELECT 1 FROM crawl_state c WHERE c.key = 'danmaku:' || r.bvid AND c.status = 'done'"
        ") ORDER BY r.view DESC"
    )
    params: tuple[Any, ...] = ()
    if limit is not None:
        sql += " LIMIT ?"
        params = (int(limit),)

    rows = conn.execute(sql, params).fetchall()
    report = DanmakuReport(targets=len(rows))
    consecutive_failures = 0

    for index, row in enumerate(rows, 1):
        bvid = row["bvid"]
        key = f"danmaku:{bvid}"
        try:
            items = client.danmaku(row["cid"])
        except BiliApiError as exc:
            set_crawl_state(conn, key, STATE_FAILED, error=str(exc))
            report.failed += 1
            report.failed_items.append({"bvid": bvid, "error": str(exc)})
            consecutive_failures += 1
            if exc.retryable and consecutive_failures >= 10:
                report.aborted = True
                break
            continue

        consecutive_failures = 0
        unique = list(dict.fromkeys(item for item in items if item))[:1200]
        if unique:
            cursor = conn.executemany(
                "INSERT OR IGNORE INTO raw_danmaku (bvid, content) VALUES (?, ?)",
                [(bvid, text) for text in unique],
            )
            report.inserted += cursor.rowcount or 0
            conn.commit()

        set_crawl_state(conn, key, STATE_DONE)
        report.done += 1

        if index % batch_size == 0:
            LOGGER.info(
                "danmaku 进度 %d/%d，完成 %d，失败 %d，弹幕 %d 条",
                index,
                len(rows),
                report.done,
                report.failed,
                report.inserted,
            )

    if report_dir is not None:
        report_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        (report_dir / f"danmaku-{stamp}.json").write_text(
            json.dumps(report.as_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return report


def summarize_danmaku(report: DanmakuReport) -> str:
    return (
        f"目标 {report.targets}，完成 {report.done}，失败 {report.failed}，"
        f"入库弹幕 {report.inserted} 条"
    )


__all__ = [
    "CollectReport",
    "DanmakuReport",
    "EnrichReport",
    "collect_danmaku",
    "collect_enrich",
    "collect_search",
    "normalize_search_item",
    "open_connection",
    "parse_duration",
    "read_keywords",
    "summarize",
    "summarize_danmaku",
    "summarize_enrich",
]
