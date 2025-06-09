import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Sequence

from autogen import ChatResult
from loguru import logger

from rubberduck.autogen.leader_executor.utils.helpers import format_chat_history


def setup_logger(run_id: str = None):
    base_log_dir = Path(__file__).resolve().parents[5] / "logs"
    date_folder = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    run_folder = f"run_{timestamp}"
    if run_id:
        run_folder += f"_{run_id}"

    log_dir = base_log_dir / date_folder / run_folder
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "console.log"

    logger.remove()  # Remove default logger configuration
    logger.add(
        log_file,
        rotation="10 MB",  # Rotate logs after reaching 10 MB
        retention=3,  # Keep up to 3 rotated logs
        enqueue=True,  # For thread-safe logging
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} - {message}",
        level="INFO",
    )

    # Also log to console
    logger.add(
        lambda msg: print(msg, end=""),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} - {message}",
        level="INFO",
    )

    return logger, log_dir


def dump_memory(memory: Dict[str, Any], log_dir: Path, skip_keys: Sequence[str] = ()) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    for node_name, entries in memory.items():
        if node_name in skip_keys or not isinstance(entries, list):
            continue
        for idx, entry in enumerate(entries, 1):
            if isinstance(entry, ChatResult):
                (log_dir / f"{node_name}_{idx}.txt").write_text(
                    format_chat_history(entry),
                    encoding="utf-8",
                )
                continue
            if isinstance(entry, str):
                (log_dir / f"{node_name}_{idx}.txt").write_text(
                    entry,
                    encoding="utf-8",
                )
                continue
            with (log_dir / f"{node_name}_{idx}.json").open("w", encoding="utf-8") as fh:
                json.dump(entry, fh, default=str, indent=2)
