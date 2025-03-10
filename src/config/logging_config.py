import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


class LoggingConfig:
    BASE_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"

    @staticmethod
    def setup_run_logging(run_id: str = None):
        date_folder = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        run_folder_name = f"run_{timestamp}"
        if run_id:
            run_folder_name += f"_{run_id}"

        run_dir = LoggingConfig.BASE_LOG_DIR / date_folder / run_folder_name
        run_dir.mkdir(parents=True, exist_ok=True)

        agents_log_dir = run_dir / "agents"
        agents_log_dir.mkdir(parents=True, exist_ok=True)

        console_log_file = run_dir / "console.log"

        log_format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                RotatingFileHandler(console_log_file, maxBytes=10 * 1024 * 1024, backupCount=3),
                logging.StreamHandler(),
            ],
        )

        return agents_log_dir
