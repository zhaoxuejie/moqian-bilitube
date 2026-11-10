"""配置加载：.env + 环境变量 + 默认值。

原则：缺少可选配置时告警而不崩溃，只有真正用到该能力时才失败。
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_DATA_DIR = Path("data")
DEFAULT_LOG_LEVEL = "INFO"


@dataclass(frozen=True)
class Config:
    """运行时配置，全部来自环境变量，可被 .env 覆盖。"""

    data_dir: Path = DEFAULT_DATA_DIR
    log_level: str = DEFAULT_LOG_LEVEL
    bili_sessdata: str | None = None
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    request_timeout: float = 20.0
    rate_limit_rps: float = 0.8

    def __post_init__(self) -> None:
        # data_dir 可能来自命令行字符串，统一收敛为 Path
        object.__setattr__(self, "data_dir", Path(self.data_dir))

    @classmethod
    def load(
        cls,
        env_file: Path | str | None = None,
        logger: logging.Logger | None = None,
    ) -> "Config":
        """加载配置；env_file 为空时读取工作目录下的 .env（可选）。"""
        load_dotenv(dotenv_path=env_file, override=False)

        config = cls(
            data_dir=Path(os.getenv("DATA_DIR") or DEFAULT_DATA_DIR),
            log_level=(os.getenv("LOG_LEVEL") or DEFAULT_LOG_LEVEL).upper(),
            bili_sessdata=os.getenv("BILI_SESSDATA") or None,
            llm_api_key=os.getenv("LLM_API_KEY") or None,
            llm_base_url=os.getenv("LLM_BASE_URL") or "https://api.deepseek.com",
            llm_model=os.getenv("LLM_MODEL") or "deepseek-chat",
            request_timeout=float(os.getenv("REQUEST_TIMEOUT") or 20),
            rate_limit_rps=float(os.getenv("RATE_LIMIT_RPS") or 0.8),
        )

        log = logger or logging.getLogger(__name__)
        if config.bili_sessdata is None:
            log.warning("未配置 BILI_SESSDATA，字幕接口不可用，第三层评估将降级")
        if config.llm_api_key is None:
            log.warning("未配置 LLM_API_KEY，评分与卡片生成在后续任务中将不可用")
        return config

    @property
    def db_path(self) -> Path:
        return self.data_dir / "bilitube.db"

    @property
    def log_dir(self) -> Path:
        return self.data_dir / "logs"
