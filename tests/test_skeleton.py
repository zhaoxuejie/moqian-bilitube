"""TASK-001 验收：CLI 入口、配置加载、日志落盘。全部离线，不依赖网络。"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from bilitube.config import Config
from bilitube.logging import setup_logging

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_KEYS = (
    "DATA_DIR",
    "LOG_LEVEL",
    "BILI_SESSDATA",
    "LLM_API_KEY",
    "REQUEST_TIMEOUT",
    "RATE_LIMIT_RPS",
)


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "bilitube", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


def clear_env(monkeypatch) -> None:
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_help_lists_all_commands() -> None:
    result = run_cli("--help")
    assert result.returncode == 0
    for command in ("collect", "normalize", "score", "card", "export", "report"):
        assert command in result.stdout


def test_unknown_command_exits_2() -> None:
    result = run_cli("bogus")
    assert result.returncode == 2


def test_placeholder_command_exits_1_and_writes_log(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    result = run_cli("report", "--data-dir", str(data_dir))
    assert "Traceback" not in result.stderr, result.stderr
    assert result.returncode == 1
    log_files = list((data_dir / "logs").glob("*.log"))
    assert log_files, "日志文件未生成"
    assert "尚未实现" in log_files[0].read_text(encoding="utf-8")


def test_config_defaults_without_env_file(tmp_path: Path, monkeypatch) -> None:
    clear_env(monkeypatch)
    config = Config.load(env_file=tmp_path / "missing.env", logger=logging.getLogger("test"))
    assert config.data_dir == Path("data")
    assert config.bili_sessdata is None
    assert config.llm_api_key is None
    assert config.rate_limit_rps == 0.8


def test_config_reads_env_file(tmp_path: Path, monkeypatch) -> None:
    clear_env(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATA_DIR=custom-data\nBILI_SESSDATA=token-123\nLLM_API_KEY=sk-test\nRATE_LIMIT_RPS=2.5\n",
        encoding="utf-8",
    )
    config = Config.load(env_file=env_file, logger=logging.getLogger("test"))
    assert config.data_dir == Path("custom-data")
    assert config.bili_sessdata == "token-123"
    assert config.llm_api_key == "sk-test"
    assert config.rate_limit_rps == 2.5


def test_logging_creates_dated_file(tmp_path: Path) -> None:
    logger = setup_logging(tmp_path, "INFO")
    logger.info("hello-log")
    log_files = list(tmp_path.glob("*.log"))
    assert len(log_files) == 1
    assert "hello-log" in log_files[0].read_text(encoding="utf-8")
