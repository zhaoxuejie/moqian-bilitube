"""相关性过滤与硬过滤：把候选池里的噪音挡在打分之前。

规则全部来自配方（presets/<name>/rules.json），改词表不需要改代码。
状态：passed（通过）、review（需人工/LLM 复核）、rejected（拒绝，附原因）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

STATUS_PASSED = "passed"
STATUS_REVIEW = "review"
STATUS_REJECTED = "rejected"

LONG_DURATION_SECONDS = 3 * 3600


@dataclass
class FilterReport:
    total: int = 0
    passed: int = 0
    review: int = 0
    rejected: int = 0
    reasons: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "review": self.review,
            "rejected": self.rejected,
            "reasons": dict(sorted(self.reasons.items(), key=lambda kv: -kv[1])),
        }


def load_rules(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _match(text: str, terms: list[str]) -> str | None:
    for term in terms:
        if term and term.lower() in text:
            return term
    return None


def decide(video: dict[str, Any], rules: dict[str, Any]) -> tuple[str, str]:
    """对单条视频做规则判定，返回 (status, reason)。"""
    title = (video.get("title") or "").lower()
    tname = video.get("tname") or ""
    duration = video.get("duration") or 0

    if duration < rules.get("min_duration_seconds", 180):
        return STATUS_REJECTED, "duration_too_short"

    allowed = rules.get("allowed_tnames") or []
    if allowed and tname not in allowed:
        return STATUS_REJECTED, f"tname:{tname or 'unknown'}"

    ai_terms = [str(t).lower() for t in rules.get("ai_terms") or []]
    if ai_terms and _match(title, ai_terms) is None:
        return STATUS_REJECTED, "not_ai_related"

    bait = _match(title, [str(t).lower() for t in rules.get("bait_terms") or []])
    if bait:
        return STATUS_REJECTED, f"clickbait:{bait}"

    collection = _match(title, [str(t).lower() for t in rules.get("collection_terms") or []])
    if collection and duration > LONG_DURATION_SECONDS:
        return STATUS_REVIEW, f"long_collection:{collection}"

    return STATUS_PASSED, ""


def apply_filter(conn: Any, rules: dict[str, Any]) -> FilterReport:
    """对 raw_videos 全量执行过滤，结果写入 videos 表（幂等）。"""
    rows = conn.execute(
        "SELECT bvid, title, duration, "
        "COALESCE(NULLIF(tname_v2, ''), tname) AS tname, "
        "COALESCE(owner_mid, up_mid) AS mid, view "
        "FROM raw_videos"
    ).fetchall()

    report = FilterReport(total=len(rows))
    decisions: list[tuple[dict[str, Any], str, str]] = []
    for row in rows:
        video = dict(row)
        status, reason = decide(video, rules)
        decisions.append((video, status, reason))

    # 同一 UP 主通过数量上限：按播放量取前 N，其余拒绝
    quota = int(rules.get("max_videos_per_up", 5))
    passed = sorted(
        [item for item in decisions if item[1] == STATUS_PASSED],
        key=lambda item: item[0].get("view") or 0,
        reverse=True,
    )
    per_up: dict[Any, int] = {}
    over_quota: set[str] = set()
    for video, _status, _reason in passed:
        mid = video.get("mid")
        if mid is None:
            continue
        per_up[mid] = per_up.get(mid, 0) + 1
        if per_up[mid] > quota:
            over_quota.add(video["bvid"])

    final: list[tuple[str, str, str, str]] = []
    for video, status, reason in decisions:
        if status == STATUS_PASSED and video["bvid"] in over_quota:
            status, reason = STATUS_REJECTED, "up_quota"
        if status == STATUS_PASSED:
            report.passed += 1
        elif status == STATUS_REVIEW:
            report.review += 1
        else:
            report.rejected += 1
        if reason:
            report.reasons[reason] = report.reasons.get(reason, 0) + 1
        final.append((video["bvid"], status, reason, datetime.now().isoformat(timespec="seconds")))

    conn.executemany(
        "INSERT INTO videos (bvid, status, reject_reason, updated_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(bvid) DO UPDATE SET status = excluded.status, "
        "reject_reason = excluded.reject_reason, updated_at = excluded.updated_at",
        final,
    )
    conn.commit()
    return report


def summarize(report: FilterReport) -> str:
    top = ", ".join(f"{k}={v}" for k, v in list(report.as_dict()["reasons"].items())[:5])
    return (
        f"总数 {report.total}，通过 {report.passed}，待复核 {report.review}，"
        f"拒绝 {report.rejected}；主要原因：{top}"
    )
