# config/config_models.py

from typing import Optional

from joblib import Parallel
from pydantic import BaseModel, Field


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

    PARALLEL_EXECUTOR: Parallel = Field(exclude=True)

    class Config:
        arbitrary_types_allowed = True


class AgentConfig(BaseModel):
    SYSTEM_PROMPT: str
    TEMPERATURE: float = 0.0
    MODEL_NAME: Optional[str] = None  # Allows agent-specific overrides
