# config/config_models.py

from typing import Optional

from pydantic import BaseModel


class GlobalConfig(BaseModel):
    ANTHROPIC_API_KEY: str
    GEMINI_API_KEY: str
    DEEPSEEK_API_KEY: str
    OPENAI_API_KEY: str
    QWEN_API_KEY: str

    INSTANCE_ID: str
    MODEL_NAME: str

    SOURCEGRAPH_ENDPOINT: str
    SOURCEGRAPH_GQL_URL: str
    SOURCEGRAPH_API_TOKEN: str

    RELEVANCE_PROCESSOR_BATCH_SIZE: int = 5
    RELEVANCE_PROCESSOR_PARALLEL_TASKS: int = 2
    RELEVANCE_PROCESSOR_MAX_RETRIES: int = 3


class AgentConfig(BaseModel):
    SYSTEM_PROMPT: str
    TEMPERATURE: float = 0.0
    MODEL_NAME: Optional[str] = None  # Allows agent-specific overrides
