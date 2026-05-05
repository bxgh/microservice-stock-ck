import os
import sys
import logging
from loguru import logger
from ..config.settings import settings

def setup_logger():
    """
    配置 Loguru 日志
    """
    # 移除默认处理器
    logger.remove()
    
    # 获取日志级别
    log_level = settings.LOG_LEVEL.upper()
    
    # 终端输出 (彩色)
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )
    
    # 文件输出 (按天滚动)
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    logger.add(
        os.path.join(log_dir, "cci_monitor_{time:YYYY-MM-DD}.log"),
        level=log_level,
        rotation="00:00",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        encoding="utf-8",
    )
    
    # 劫持标准 logging
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    return logger

# 预设一个全局 logger，但在 main.py 启动时会调用 setup_logger
cci_logger = logger
