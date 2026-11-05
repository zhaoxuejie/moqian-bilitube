"""LLM 内容理解与卡片生成。

输入：标题、简介、分区、时长、弹幕采样。
输出：结构化卡片（verdict / quality / summary / why / audience / prereq /
difficulty / freshness / topics），并把 quality 写回 scores.content，
按 0.6 × machine + 0.4 × content 重算 total（ADR-002、ADR-013）。
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from .preset import Preset
from .scoring import CONTENT_WEIGHT, MACHINE_WEIGHT

LOGGER = logging.getLogger("bilitube")

DANMAKU_SAMPLE = 200
MIN_DANMAKU_LEN = 4

# 引擎默认提示词：只保留「输出契约」，不含任何领域判定标准。
# 真正的判定标准放在 presets/<name>/prompt.md，由 preset 传进来。
SYSTEM_PROMPT = """你是内容策展编辑，负责判断一条视频是否值得观看。

只输出一个 JSON 对象，不要任何解释、不要 markdown 代码块。字段：
{
  "verdict": "教程|实战|测评|新闻|水|搬运",
  "quality": 0-100 的整数，表示内容密度与可复用性（不是播放量）,
  "summary": "40 字以内的内容摘要",
  "why": "50 字以内说明为什么值得或不值得看",
  "audience": "适合谁看，20 字以内",
  "prereq": "需要的前置知识，20 字以内，没有则写 无",
  "difficulty": 1-5 的整数,
  "freshness": "evergreen|aging|outdated",
  "topics": ["2-5 个主题词"]
}
"""


class LlmError(RuntimeError):
    pass


@dataclass
class LlmCard:
    bvid: str
    verdict: str
    quality: int
    summary: str
    why: str
    audience: str
    prereq: str
    difficulty: int
    freshness: str
    topics: list[str]
    model: str

    def as_payload(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "quality": self.quality,
            "summary": self.summary,
            "why": self.why,
            "audience": self.audience,
            "prereq": self.prereq,
            "difficulty": self.difficulty,
            "freshness": self.freshness,
            "topics": self.topics,
            "model": self.model,
            "evidence": "danmaku+meta",
        }


@dataclass
class CardReport:
    targets: int = 0
    done: int = 0
    failed: int = 0
    skipped: int = 0
    avg_quality: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    elapsed_sec: float = 0.0
    failed_items: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "targets": self.targets,
            "done": self.done,
            "failed": self.failed,
            "skipped": self.skipped,
            "avg_quality": round(self.avg_quality, 2),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "elapsed_sec": round(self.elapsed_sec, 1),
            "failed_items": self.failed_items,
        }


def parse_json_response(text: str) -> dict[str, Any]:
    """从模型输出里抠出 JSON；容忍代码块包裹与前后废话。"""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LlmError(f"无法解析 JSON: {text[:120]}")
    return json.loads(cleaned[start : end + 1])


def build_prompt(row: dict[str, Any], danmaku: list[str]) -> str:
    sampled = [item for item in danmaku if len(item) >= MIN_DANMAKU_LEN][:DANMAKU_SAMPLE]
    desc = (row.get("description") or "").strip()[:600]
    lines = [
        f"标题：{row.get('title') or ''}",
        f"分区：{row.get('tname') or ''}",
        f"时长：{row.get('duration') or 0} 秒",
        f"播放：{row.get('view') or 0}，收藏：{row.get('favorite') or 0}，投币：{row.get('coin') or 0}",
        f"简介：{desc or '（无）'}",
        "",
        "弹幕采样（可能含噪音）：",
    ]
    lines.extend(sampled[:80] if sampled else ["（无弹幕）"])
    return "\n".join(lines)


class LlmClient:
    """OpenAI 兼容的 JSON 输出客户端。"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        *,
        timeout: float = 60.0,
        retries: int = 2,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.model = model
        self.retries = retries
        self.last_usage: dict[str, int] = {}
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=timeout,
            transport=transport,
        )

    def chat_json(self, prompt: str, *, system: str = SYSTEM_PROMPT) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 600,
            "stream": False,
        }
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = self._client.post("/chat/completions", json=payload)
                response.raise_for_status()
                body = response.json()
                self.last_usage = body.get("usage") or {}
                content = body["choices"][0]["message"]["content"]
                return parse_json_response(content)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < self.retries:
                    time.sleep(2 ** attempt)
        raise LlmError(f"LLM 调用失败: {last_error}")

    def close(self) -> None:
        self._client.close()


def _to_card(bvid: str, data: dict[str, Any], model: str) -> LlmCard:
    return LlmCard(
        bvid=bvid,
        verdict=str(data.get("verdict") or "未知"),
        quality=max(0, min(100, int(data.get("quality") or 0))),
        summary=str(data.get("summary") or ""),
        why=str(data.get("why") or ""),
        audience=str(data.get("audience") or ""),
        prereq=str(data.get("prereq") or "无"),
        difficulty=max(1, min(5, int(data.get("difficulty") or 3))),
        freshness=str(data.get("freshness") or "aging"),
        topics=[str(item) for item in (data.get("topics") or [])][:5],
        model=model,
    )


def open_cards(conn: Any, model: str, limit: int | None = None) -> list[dict[str, Any]]:
    sql = (
        "SELECT r.bvid, r.title, r.description, r.duration, r.view, r.favorite, r.coin, "
        "COALESCE(NULLIF(r.tname_v2, ''), r.tname, 'unknown') AS tname, s.machine "
        "FROM raw_videos r JOIN videos v ON v.bvid = r.bvid AND v.status = 'passed' "
        "LEFT JOIN scores s ON s.bvid = r.bvid "
        "LEFT JOIN cards c ON c.bvid = r.bvid "
        "WHERE c.bvid IS NULL OR json_extract(c.payload, '$.model') != ? "
        "ORDER BY COALESCE(s.total, 0) DESC"
    )
    params: list[Any] = [model]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(int(limit))
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def danmaku_for(conn: Any, bvid: str, limit: int = 400) -> list[str]:
    rows = conn.execute(
        "SELECT content FROM raw_danmaku WHERE bvid = ? LIMIT ?", (bvid, limit)
    ).fetchall()
    return [row["content"] for row in rows]


def save_card(conn: Any, card: LlmCard, machine: float | None) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "INSERT INTO cards (bvid, payload, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(bvid) DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at",
        (card.bvid, json.dumps(card.as_payload(), ensure_ascii=False), now),
    )
    base = machine if machine is not None else 0.0
    total = MACHINE_WEIGHT * base + CONTENT_WEIGHT * card.quality
    conn.execute(
        "INSERT INTO scores (bvid, content, machine, total, flags, updated_at) "
        "VALUES (?, ?, ?, ?, '', ?) "
        "ON CONFLICT(bvid) DO UPDATE SET content = excluded.content, "
        "total = excluded.total, updated_at = excluded.updated_at",
        (card.bvid, card.quality, base, total, now),
    )
    conn.commit()


def run_cards(
    llm: Any,
    conn: Any,
    *,
    model: str,
    limit: int | None = None,
    batch_size: int = 20,
    report_dir: Path | None = None,
    preset: Preset | None = None,
) -> CardReport:
    system_prompt = preset.prompt if preset is not None else SYSTEM_PROMPT
    if preset is not None:
        LOGGER.info("card 使用配方 %s（%s）", preset.label, preset.path)
    rows = open_cards(conn, model, limit)
    report = CardReport(targets=len(rows))
    started = time.monotonic()
    qualities: list[int] = []

    for index, row in enumerate(rows, 1):
        bvid = row["bvid"]
        prompt = build_prompt(row, danmaku_for(conn, bvid))
        try:
            data = llm.chat_json(prompt, system=system_prompt)
            card = _to_card(bvid, data, model)
        except LlmError as exc:
            report.failed += 1
            report.failed_items.append({"bvid": bvid, "error": str(exc)[:200]})
            continue

        save_card(conn, card, row.get("machine"))
        report.done += 1
        qualities.append(card.quality)
        usage = getattr(llm, "last_usage", {}) or {}
        report.prompt_tokens += int(usage.get("prompt_tokens") or 0)
        report.completion_tokens += int(usage.get("completion_tokens") or 0)

        if index % batch_size == 0:
            LOGGER.info(
                "card 进度 %d/%d，完成 %d，失败 %d，平均质量 %.1f",
                index,
                len(rows),
                report.done,
                report.failed,
                sum(qualities) / max(1, len(qualities)),
            )

    report.avg_quality = sum(qualities) / max(1, len(qualities))
    report.elapsed_sec = time.monotonic() - started

    if report_dir is not None:
        report_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        (report_dir / f"cards-{stamp}.json").write_text(
            json.dumps(report.as_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return report


def summarize(report: CardReport) -> str:
    return (
        f"目标 {report.targets}，完成 {report.done}，失败 {report.failed}，"
        f"平均质量 {report.avg_quality:.1f}，tokens {report.prompt_tokens + report.completion_tokens}，"
        f"耗时 {report.elapsed_sec:.0f}s"
    )
