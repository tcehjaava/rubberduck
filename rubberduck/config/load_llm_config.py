import os
from typing import List

from autogen import config_list_from_json
from loguru import logger


def load_llm_config(model_config: str = "default_executor") -> List[dict]:
    module_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(module_dir, "..", "config")
    config_path = os.path.join(config_dir, f"{model_config}.json")

    try:
        config_list = config_list_from_json(env_or_file=config_path)
        logger.info("Loaded model config from: %s", config_path)
        return config_list
    except Exception as exc:
        logger.error("Failed to load model config '%s': %s", model_config, exc, exc_info=True)
        raise ValueError(f"Could not load model configuration: {exc}") from exc
