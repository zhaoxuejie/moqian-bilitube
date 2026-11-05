"""配方（preset）：把「按什么标准跑」从代码里拆出来。

一个 preset 是一个目录，结构固定：

    presets/<name>/
    ├── preset.json    元信息与文件索引（name / version / description + 各文件名）
    ├── keywords.txt   采集关键词，每行一个，# 开头为注释
    ├── rules.json     过滤规则（词表、分区白名单、时长门槛、单 UP 配额）
    ├── scoring.json   打分权重、时长分桶、小样本阈值
    └── prompt.md      生成卡片用的 system prompt

代码（引擎）只认这个结构，不认识具体内容；换一套目录就是换一个领域。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PRESET_FILE = "preset.json"
DEFAULT_PRESET_PATH = Path("presets/ai-video")

Bucket = tuple[int, int | None, str]


@dataclass(frozen=True)
class Preset:
    name: str
    version: str
    description: str
    path: Path
    keywords: tuple[str, ...]
    rules: dict[str, Any]
    rules_path: Path
    weights: dict[str, float]
    buckets: tuple[Bucket, ...]
    min_group_size: int
    prompt: str

    @property
    def label(self) -> str:
        """用于日志与卡片溯源，例如 ai-video@v1。"""
        return f"{self.name}@{self.version}"


class PresetError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise PresetError(f"缺少文件: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PresetError(f"JSON 解析失败 {path}: {exc}") from exc


def read_keywords(path: Path) -> tuple[str, ...]:
    """跳过空行与 # 注释。"""
    if not path.exists():
        raise PresetError(f"缺少关键词文件: {path}")
    items: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        items.append(line)
    return tuple(items)


def load_preset(path: Path | str = DEFAULT_PRESET_PATH) -> Preset:
    root = Path(path)
    manifest = _read_json(root / PRESET_FILE)
    rules_path = root / str(manifest.get("rules") or "rules.json")
    scoring = _read_json(root / str(manifest.get("scoring") or "scoring.json"))

    keywords = read_keywords(root / str(manifest.get("keywords") or "keywords.txt"))
    if not keywords:
        raise PresetError(f"{root}: 关键词为空")

    prompt_path = root / str(manifest.get("prompt") or "prompt.md")
    if not prompt_path.exists():
        raise PresetError(f"缺少 prompt: {prompt_path}")
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    if not prompt:
        raise PresetError(f"{prompt_path}: prompt 为空")

    weights = {str(key): float(value) for key, value in (scoring.get("weights") or {}).items()}
    if not weights:
        raise PresetError(f"{root}: scoring.weights 为空")
    total = sum(weights.values())
    if abs(total - 1.0) > 0.01:
        raise PresetError(f"{root}: 权重之和应为 1.0，当前 {total:.3f}")

    buckets: tuple[Bucket, ...] = tuple(
        (int(item[0]), None if item[1] is None else int(item[1]), str(item[2]))
        for item in (scoring.get("buckets") or [])
    )
    if not buckets:
        raise PresetError(f"{root}: scoring.buckets 为空")

    return Preset(
        name=str(manifest.get("name") or root.name),
        version=str(manifest.get("version") or "v0"),
        description=str(manifest.get("description") or ""),
        path=root,
        keywords=keywords,
        rules=_read_json(rules_path),
        rules_path=rules_path,
        weights=weights,
        buckets=buckets,
        min_group_size=int(scoring.get("min_group_size") or 30),
        prompt=prompt,
    )
