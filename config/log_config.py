import os
import sys
from loguru import logger
from pathlib import Path

log_dir = Path(__file__).parent.parent / "log"
log_dir.mkdir(exist_ok=True)

log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

logger.remove()

logger.add(
    sys.stdout,
    format=log_format,
    level="INFO",
    colorize=True
)

logger.add(
    log_dir / "{time:YYYY-MM-DD}.txt",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
    rotation="00:00",
    retention="30 days",
    encoding="utf-8"
)

logger.info("日志系统初始化完成")
