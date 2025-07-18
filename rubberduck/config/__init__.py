import json
import os
from dataclasses import dataclass
from pathlib import Path

import tomllib
from autogen import LLMConfig
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(ENV_PATH, override=True)


def load_llm_config(name: str) -> LLMConfig:
    cfg_path = (Path(__file__).resolve().parent / ".." / "config" / f"{name}.json").resolve()
    data = json.loads(cfg_path.read_text())
    return LLMConfig(**data)


@dataclass
class RubberduckConfig:
    leader_model: str
    executor_model: str
    semantic_processor_model: str
    logger_model: str
    max_iterations: int
    executor_max_turns: int
    leader_max_turns: int
    recursion_limit: int


def load_rubberduck_config() -> RubberduckConfig:
    """Load Rubberduck configuration from pyproject.toml with environment variable overrides."""
    # Find pyproject.toml file
    config_path = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"

    # Load from pyproject.toml
    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    swebench_config = data.get("tool", {}).get("rubberduck", {}).get("swebench", {})

    # Apply environment variable overrides
    config = RubberduckConfig(
        leader_model=os.getenv("SWEBENCH_LEADER_MODEL", swebench_config.get("leader_model")),
        executor_model=os.getenv("SWEBENCH_EXECUTOR_MODEL", swebench_config.get("executor_model")),
        semantic_processor_model=os.getenv(
            "SWEBENCH_SEMANTIC_PROCESSOR_MODEL", swebench_config.get("semantic_processor_model")
        ),
        logger_model=os.getenv("SWEBENCH_LOGGER_MODEL", swebench_config.get("logger_model")),
        max_iterations=int(os.getenv("SWEBENCH_MAX_ITERATIONS", swebench_config.get("max_iterations", 10))),
        executor_max_turns=int(
            os.getenv("SWEBENCH_EXECUTOR_MAX_TURNS", swebench_config.get("executor_max_turns", 120))
        ),
        leader_max_turns=int(os.getenv("SWEBENCH_LEADER_MAX_TURNS", swebench_config.get("leader_max_turns", 1))),
        recursion_limit=int(os.getenv("SWEBENCH_RECURSION_LIMIT", swebench_config.get("recursion_limit", 1000))),
    )

    return config


__all__: list[str] = ["load_llm_config", "RubberduckConfig", "load_rubberduck_config"]
