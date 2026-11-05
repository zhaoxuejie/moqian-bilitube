"""配方加载：结构校验、权重和、缺文件与空配方的报错。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bilitube.preset import PresetError, load_preset
from bilitube.scoring import duration_bucket

REPO_ROOT = Path(__file__).resolve().parents[1]
SHIPPED = REPO_ROOT / "presets" / "ai-video"

# 真实配方被 .gitignore 排除，新克隆里只有 example，这时跳过即可
requires_shipped = pytest.mark.skipif(
    not SHIPPED.exists(), reason="真实配方不入库（presets/ai-video 被 gitignore）"
)


def write_preset(
    root: Path,
    *,
    weights: dict[str, float],
    keywords: str = "大模型\n",
    prompt: str = "测试用提示",
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "preset.json").write_text(
        json.dumps({"name": "tmp", "version": "v9"}), encoding="utf-8"
    )
    (root / "keywords.txt").write_text(keywords, encoding="utf-8")
    (root / "rules.json").write_text("{}", encoding="utf-8")
    (root / "prompt.md").write_text(prompt, encoding="utf-8")
    (root / "scoring.json").write_text(
        json.dumps(
            {"weights": weights, "buckets": [[0, None, "all"]], "min_group_size": 5}
        ),
        encoding="utf-8",
    )
    return root


@requires_shipped
def test_load_shipped_preset() -> None:
    preset = load_preset(SHIPPED)
    assert preset.label == "ai-video@v1"
    assert len(preset.keywords) >= 10
    assert abs(sum(preset.weights.values()) - 1.0) < 0.01
    assert len(preset.buckets) == 4
    assert preset.min_group_size >= 1
    assert preset.rules.get("allowed_tnames")
    assert preset.rules_path.name == "rules.json"
    assert preset.prompt.strip()


def test_example_preset_loads() -> None:
    """随仓库一起发布的示例配方必须永远可用。"""
    preset = load_preset(REPO_ROOT / "presets" / "example")
    assert preset.label == "example@v1"
    assert len(preset.keywords) >= 2
    assert abs(sum(preset.weights.values()) - 1.0) < 0.01
    assert set(preset.weights) <= {"fav_rate", "coin_rate", "like_rate", "talk_rate", "log_view"}
    assert preset.prompt.strip()


def test_keywords_skip_comments_and_blank_lines(tmp_path: Path) -> None:
    root = write_preset(tmp_path / "p", weights={"fav_rate": 1.0}, keywords="# 注释\n\nRAG\n\n微调\n")
    preset = load_preset(root)
    assert preset.keywords == ("RAG", "微调")


def test_missing_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(PresetError):
        load_preset(tmp_path / "not-a-preset")


def test_weights_must_sum_to_one(tmp_path: Path) -> None:
    root = write_preset(tmp_path / "p", weights={"fav_rate": 0.5, "coin_rate": 0.2})
    with pytest.raises(PresetError):
        load_preset(root)


def test_empty_keywords_raises(tmp_path: Path) -> None:
    root = write_preset(tmp_path / "p", weights={"fav_rate": 1.0}, keywords="# 只有注释\n")
    with pytest.raises(PresetError):
        load_preset(root)


def test_custom_buckets_change_grouping() -> None:
    buckets = ((0, 600, "short"), (600, None, "long"))
    assert duration_bucket(300, buckets) == "short"
    assert duration_bucket(900, buckets) == "long"
