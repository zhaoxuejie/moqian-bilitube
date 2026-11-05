"""分位归一与机器评分。

为什么用分位而不是绝对阈值：
- B 站"收藏数"与"播放数"口径不一致，收藏率可以超过 100%（ADR-009）
- 不同分区、不同时长的互动基线差异很大，绝对值不可比

做法：按「分区 × 时长档」分组，组内算分位；组内样本不足 30 条时退化为全站分位并标注。
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .preset import Preset

# 以下是引擎默认值：preset 没提供时才用，权重故意取等权占位——
# 真实权重属于配方（presets/<name>/scoring.json），不随代码发布。
# 综合分 = 0.6 × 机器分 + 0.4 × 内容分（llm.py 复用这两个常量）
MACHINE_WEIGHT = 0.6
CONTENT_WEIGHT = 0.4

MIN_GROUP_SIZE = 30

WEIGHTS = {
    "fav_rate": 0.2,
    "coin_rate": 0.2,
    "like_rate": 0.2,
    "talk_rate": 0.2,
    "log_view": 0.2,
}

BUCKETS = (
    (0, 600, "<10min"),
    (600, 1800, "10-30min"),
    (1800, 5400, "30-90min"),
    (5400, None, ">90min"),
)


@dataclass
class ScoreReport:
    total: int = 0
    scored: int = 0
    low_sample: int = 0
    avg_machine: float = 0.0
    top: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "scored": self.scored,
            "low_sample": self.low_sample,
            "avg_machine": round(self.avg_machine, 2),
            "top": self.top,
        }


def duration_bucket(
    seconds: int | None,
    buckets: tuple[tuple[int, int | None, str], ...] = BUCKETS,
) -> str:
    value = seconds or 0
    for low, high, label in buckets:
        if high is None and value >= low:
            return label
        if high is not None and low <= value < high:
            return label
    return buckets[-1][2]


def _safe_div(numerator: float | None, denominator: float | None) -> float:
    if not denominator:
        return 0.0
    return (numerator or 0) / denominator


def compute_metrics(row: dict[str, Any]) -> dict[str, float]:
    view = row.get("view") or 0
    return {
        "fav_rate": _safe_div(row.get("favorite"), view),
        "coin_rate": _safe_div(row.get("coin"), view),
        "like_rate": _safe_div(row.get("like_count"), view),
        "talk_rate": _safe_div((row.get("reply") or 0) + (row.get("danmaku") or 0), view),
        "log_view": math.log1p(max(view, 0)),
    }


def percentiles(values: list[float]) -> list[float]:
    """把一组值转成 0–100 的百分位（最小 0，最大 100）。"""
    size = len(values)
    if size == 0:
        return []
    if size == 1:
        return [50.0]
    order = sorted(range(size), key=lambda index: values[index])
    result = [0.0] * size
    for position, index in enumerate(order):
        result[index] = position / (size - 1) * 100.0
    return result


def score_all(conn: Any, preset: Preset | None = None) -> ScoreReport:
    """按 preset 的权重与分桶打分；不传 preset 时用引擎默认值。"""
    weights = dict(preset.weights) if preset else dict(WEIGHTS)
    buckets = preset.buckets if preset else BUCKETS
    min_group_size = preset.min_group_size if preset else MIN_GROUP_SIZE

    rows = [
        dict(row)
        for row in conn.execute(
            "SELECT r.bvid, r.view, r.favorite, r.coin, r.like_count, r.danmaku, r.reply, "
            "r.duration, COALESCE(NULLIF(r.tname_v2, ''), r.tname, 'unknown') AS tname "
            "FROM raw_videos r JOIN videos v ON v.bvid = r.bvid WHERE v.status = 'passed'"
        ).fetchall()
    ]
    report = ScoreReport(total=len(rows))
    if not rows:
        return report

    metrics = {row["bvid"]: compute_metrics(row) for row in rows}
    groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        key = f"{row['tname']}|{duration_bucket(row['duration'], buckets)}"
        groups[key].append(row["bvid"])

    global_scores: dict[str, dict[str, float]] = {}
    for metric in weights:
        values = [metrics[bvid][metric] for bvid in metrics]
        for bvid, pct in zip(metrics.keys(), percentiles(values)):
            global_scores.setdefault(bvid, {})[metric] = pct

    group_scores: dict[str, dict[str, float]] = {}
    low_sample_bvids: set[str] = set()
    for key, bvids in groups.items():
        if len(bvids) < min_group_size:
            for bvid in bvids:
                group_scores[bvid] = dict(global_scores[bvid])
                low_sample_bvids.add(bvid)
            continue
        for metric in weights:
            values = [metrics[bvid][metric] for bvid in bvids]
            for bvid, pct in zip(bvids, percentiles(values)):
                group_scores.setdefault(bvid, {})[metric] = pct

    scored: list[tuple[Any, ...]] = []
    now = datetime.now().isoformat(timespec="seconds")
    total_score = 0.0
    for row in rows:
        bvid = row["bvid"]
        parts = group_scores[bvid]
        machine = sum(weight * parts[metric] for metric, weight in weights.items())
        flags: list[str] = []
        if bvid in low_sample_bvids:
            flags.append("low_sample")
        if (row.get("coin") or 0) == 0:
            flags.append("zero_coin")
        if metrics[bvid]["fav_rate"] > 1.0:
            flags.append("fav_over_view")
        scored.append(
            (
                bvid,
                None,
                round(machine, 2),
                round(machine, 2),
                json.dumps(flags, ensure_ascii=False),
                now,
            )
        )
        total_score += machine

    # 重新打分时不能把已有的内容分抹掉：content 用 COALESCE 保留旧值，
    # total 在有内容分时按 0.6 × 机器分 + 0.4 × 内容分重算。
    blend = (
        f"ROUND({MACHINE_WEIGHT} * excluded.machine + {CONTENT_WEIGHT} * scores.content, 4)"
    )
    conn.executemany(
        "INSERT INTO scores (bvid, content, machine, total, flags, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(bvid) DO UPDATE SET "
        "content = COALESCE(scores.content, excluded.content), "
        "machine = excluded.machine, "
        f"total = CASE WHEN scores.content IS NULL THEN excluded.total ELSE {blend} END, "
        "flags = excluded.flags, updated_at = excluded.updated_at",
        scored,
    )
    conn.commit()

    report.scored = len(scored)
    report.low_sample = len(low_sample_bvids)
    report.avg_machine = total_score / max(1, len(scored))
    top_rows = conn.execute(
        "SELECT s.bvid, s.machine, s.total, s.flags, r.title, r.view "
        "FROM scores s JOIN raw_videos r ON r.bvid = s.bvid "
        "ORDER BY s.total DESC LIMIT 20"
    ).fetchall()
    report.top = [
        {
            "bvid": row["bvid"],
            "machine": row["machine"],
            "total": row["total"],
            "flags": row["flags"],
            "title": row["title"],
            "view": row["view"],
        }
        for row in top_rows
    ]
    return report


def summarize(report: ScoreReport) -> str:
    return (
        f"参评 {report.total}，完成评分 {report.scored}，"
        f"样本不足 {report.low_sample}，机器均分 {report.avg_machine:.1f}"
    )
