"""
日志配置工具
"""
import os
import sys
from loguru import logger

def setup_logger(log_level: str = "INFO", log_dir: str = "./data"):
    """配置 loguru 日志输出"""
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "bilibili_ops.log")

    # 适配 Windows 控制台编码
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    logger.remove()
    # 控制台输出
    logger.add(
        sys.stdout,
        level=log_level.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
        enqueue=True
    )
    # 文件输出
    logger.add(
        log_file,
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
        enqueue=True
    )
    return logger
