from typing import Any, Dict, Type

from pydantic import BaseModel

from .executor import ExecutorReport, ExecutorTaskSpec
from .leader import LeaderReviewResponse
from .swebench import SWEBenchVerifiedInstance


def build_schema(model: Type[BaseModel]) -> Dict[str, Any]:
    return model.model_json_schema()


__all__ = [
    "SWEBenchVerifiedInstance",
    "LeaderReviewResponse",
    "ExecutorTaskSpec",
    "ExecutorReport",
    "build_schema",
]
