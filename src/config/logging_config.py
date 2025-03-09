# config/logging_config.py

import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


class LoggingConfig:
    LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
    LOG_DIR.mkdir(exist_ok=True)

    @staticmethod
    def setup_run_logging(run_id: str = None):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"workflow_{timestamp}"
        if run_id:
            filename += f"_{run_id}"
        log_file = LoggingConfig.LOG_DIR / f"{filename}.log"

        log_format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=3),
                logging.StreamHandler(),
            ],
        )
