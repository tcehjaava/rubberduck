import os
import pprint
from typing import List

from autogen import config_list_from_json
from dotenv import load_dotenv
from loguru import logger

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(ENV_PATH, override=True)


def load_llm_config(model_config: str = "default_executor") -> List[dict]:
    module_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(module_dir, "..", "config")
    config_path = os.path.join(config_dir, f"{model_config}.json")

    try:
        config_list = config_list_from_json(env_or_file=config_path)
        logger.info("Loaded model config from: {}", config_path)

        pretty = pprint.pformat(config_list, compact=True, width=100)
        logger.debug("Resolved config: {}", pretty)

        return config_list

    except Exception as exc:
        logger.exception("Failed to load model config '{}': {}", model_config, exc)
        raise ValueError(f"Could not load model configuration: {exc}") from exc


__all__: list[str] = ["load_llm_config"]
