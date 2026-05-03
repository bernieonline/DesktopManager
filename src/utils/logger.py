import logging
import os
from logging.handlers import TimedRotatingFileHandler

def get_logger(module_name: str) -> logging.Logger:
    logger = logging.getLogger(module_name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    log_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "DesktopWorkspaces", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "app.log")

    file_handler = TimedRotatingFileHandler(
        log_path, when="midnight", backupCount=7, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        "[%(levelname)s] [%(name)s] %(message)s"
    ))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
