"""TASK-009 验收：JSON 解析、卡片落库、分数重算、幂等跳过。不产生真实费用。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bilitube.db import connect, init_db
from bilitube.llm import (
    LlmError,
    build_prompt,
    parse_json_response,
    run_cards,
)

GOOD = {
    "verdict": "教程",
    "quality": 82,
    "summary": "从零讲清 RAG 的检索与重排",
    "why": "有代码演示，步骤完整",
    "audience": "有 Python 基础的开发者",
    "prereq": "Python、HTTP",
    "difficulty": 3,
    "freshness": "evergreen",
    "topics": ["RAG", "检索"],
}


class FakeLlm:
    model = "fake-model"
    last_usage = {"prompt_tokens": 500, "completion_tokens": 120}

    def __init__(self, data=None, error: Exception | None = None):
        self.data = data or GOOD
        self.error = error

    def chat_json(self, prompt: str, system: str | None = None) -> dict:
        if self.error:
            raise self.error
        return self.data


def test_parse_json_plain() -> None:
    assert parse_json_response('{"a": 1}')["a"] == 1


def test_parse_json_with_code_fence() -> None:
    text = '```json\n{"a": 2}\n```'
    assert parse_json_response(text)["a"] == 2


def test_parse_json_with_chatter() -> None:
    text = '好的，结果如下：{"a": 3} 希望有帮助'
    assert parse_json_response(text)["a"] == 3


def test_parse_json_invalid() -> None:
    with pytest.raises(LlmError):
        parse_json_response("没有 JSON")


def test_build_prompt_filters_short_danmaku() -> None:
    row = {"title": "RAG 教程", "description": "简介", "tname": "计算机技术", "duration": 600}
    prompt = build_prompt(row, ["好", "这个方法讲得很清楚", "1", "真实弹幕内容"])
    assert "这个方法讲得很清楚" in prompt
    assert "真实弹幕内容" in prompt
    assert "\n1\n" not in prompt


def open_db(tmp_path: Path):
    conn = connect(tmp_path / "bilitube.db")
    init_db(conn)
    return conn


def seed(conn, bvid: str = "BV1", machine: float = 60.0) -> None:
    conn.execute(
        "INSERT INTO raw_videos (bvid, title, description, duration, view, favorite, coin, tname, collected_at) "
        "VALUES (?, '大模型 RAG 教程', '讲解检索增强', 900, 10000, 500, 100, '计算机技术', '')",
        (bvid,),
    )
    conn.execute("INSERT INTO videos (bvid, status, updated_at) VALUES (?, 'passed', '')", (bvid,))
    conn.execute(
        "INSERT INTO scores (bvid, content, machine, total, flags, updated_at) "
        "VALUES (?, NULL, ?, ?, '', '')",
        (bvid, machine, machine),
    )
    conn.executemany(
        "INSERT INTO raw_danmaku (bvid, content) VALUES (?, ?)",
        [(bvid, "讲得很清楚"), (bvid, "这部分有代码演示")],
    )
    conn.commit()


def test_run_cards_writes_card_and_recomputes_total(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    seed(conn, "BV1", machine=60.0)

    report = run_cards(FakeLlm(), conn, model="fake-model")
    assert report.done == 1
    assert report.failed == 0
    assert report.prompt_tokens == 500

    payload = json.loads(conn.execute("SELECT payload FROM cards WHERE bvid='BV1'").fetchone()["payload"])
    assert payload["quality"] == 82
    assert payload["model"] == "fake-model"

    row = conn.execute("SELECT content, machine, total FROM scores WHERE bvid='BV1'").fetchone()
    assert row["content"] == 82
    assert abs(row["total"] - (0.6 * 60 + 0.4 * 82)) < 0.01
    conn.close()


def test_run_cards_is_idempotent(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    seed(conn)
    first = run_cards(FakeLlm(), conn, model="fake-model")
    second = run_cards(FakeLlm(), conn, model="fake-model")
    assert first.done == 1
    assert second.targets == 0
    assert second.done == 0
    conn.close()


def test_run_cards_counts_failures(tmp_path: Path) -> None:
    conn = open_db(tmp_path)
    seed(conn)
    report = run_cards(FakeLlm(error=LlmError("boom")), conn, model="fake-model")
    assert report.failed == 1
    assert report.done == 0
    assert conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0] == 0
    conn.close()
