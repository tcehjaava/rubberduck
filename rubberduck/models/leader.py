from __future__ import annotations

from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class LeaderTaskSpec(BaseModel):
    type: Literal["leader_task"] = Field(
        default="leader_task",
        description="Discriminator identifying a LeaderTaskSpec object.",
    )
    instructions: str = Field(
        ...,
        description="Step-by-step instructions for the Executor to follow.",
        example="""1. List all files in /workspace/project/src
2. Search for 'TODO' in those files
3. Extract the surrounding context for each occurrence""",
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Explanation of why the Leader produced this task.",
    )
    context: Optional[List[str]] = Field(
        default=None,
        description="Relevant file paths or previous findings.",
    )


class LeaderReport(BaseModel):
    type: Literal["leader_report"] = Field(
        default="leader_report",
        description="Discriminator identifying a LeaderReport object.",
    )
    summary: str = Field(
        ...,
        description="Concise summary of the overall outcome.",
    )
    details: str = Field(
        ...,
        description="Detailed explanation of the steps taken.",
    )
    diff: Optional[str] = Field(
        default=None,
        description="Optional diff of code changes produced by the Executor.",
    )


LeaderOutput = Annotated[Union[LeaderTaskSpec, LeaderReport], Field(discriminator="type")]
