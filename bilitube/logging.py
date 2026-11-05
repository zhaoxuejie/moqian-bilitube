"""日志：同时输出到 stdout 与按天滚动的文件。"""

from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s | %(message)s"
DATE_FORMAT = "%H:%M:%S"
LOGGER_NAME = "bilitube"


def setup_logging(log_dir: Path, level: str = "INFO") -> logging.Logger:
    """创建（或重建）bilitube 日志器，返回可直接使用的实例。"""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{date.today().isoformat()}.log"

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logger.propagate = False
    return logger


def get_logger() -> logging.Logger:
    """取已配置的日志器；未配置时退回标准库默认行为。"""
    return logging.getLogger(LOGGER_NAME)
