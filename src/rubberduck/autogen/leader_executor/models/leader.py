from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class LeaderTaskSpec(BaseModel):
    reasoning: Optional[str] = Field(
        default=None,
        description="Detailed Explanation of why the Leader produced this task.",
    )
    task: str = Field(
        ...,
        description="A single task to be delegated.",
        example="List all files in /workspace/project/src and extract TODOs",
    )


class LeaderReport(BaseModel):
    status: Literal["success", "failure", "partial", "terminated"] = Field(
        ...,
        description="Overall status of the task execution.",
    )
    summary: str = Field(
        ...,
        description="Concise summary of the overall outcome.",
    )
    diff: str = Field(
        ...,
        description="This is the output of the `git diff` command.",
    )
