import json
import os
from pathlib import Path

from autogen import LLMConfig
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(ENV_PATH, override=True)


def load_llm_config(name: str) -> LLMConfig:
    cfg_path = (Path(__file__).resolve().parent / ".." / "config" / f"{name}.json").resolve()
    data = json.loads(cfg_path.read_text())
    return LLMConfig(**data)


__all__: list[str] = ["load_llm_config"]
