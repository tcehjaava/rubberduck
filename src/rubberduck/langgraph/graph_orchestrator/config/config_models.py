from typing import Optional

from joblib import Parallel
from pydantic import BaseModel, Field


class GlobalConfig(BaseModel):
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    QWEN_API_KEY: Optional[str] = None

    INSTANCE_ID: str
    MODEL_NAME: str

    SOURCEGRAPH_ENDPOINT: str
    SOURCEGRAPH_GQL_URL: str
    SOURCEGRAPH_API_TOKEN: Optional[str] = None

    PARALLEL_EXECUTOR: Parallel = Field(exclude=True)

    class Config:
        arbitrary_types_allowed = True


class AgentConfig(BaseModel):
    SYSTEM_PROMPT: str
    TEMPERATURE: float = 0.0
    MODEL_NAME: Optional[str] = None  # Allows agent-specific overrides
