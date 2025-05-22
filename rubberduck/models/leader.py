from __future__ import annotations

from typing import List, Optional, Union, Literal, Annotated
from pydantic import BaseModel, Field


class LeaderTaskSpec(BaseModel):
    """Task details produced by the Leader for the Executor."""

    type: Literal["leader_task"] = Field(
        default="leader_task",
        description="Discriminator identifying a LeaderTaskSpec object.",
    )
    instructions: str = Field(
        ...,
        description="Step-by-step instructions for the Executor to follow.",
        example="1. List all files in /workspace/project/src\n2. Search for 'TODO' in those files",
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Explanation of why the Leader produced this task.",
        example="Scanning for TODO comments helps locate unfinished features.",
    )
    context: Optional[List[str]] = Field(
        default=None,
        description="Relevant file paths or previous findings.",
        example=["project/src/module.py"],
    )
    expected_output: Optional[str] = Field(
        default=None,
        description="Description of what the Executor should return.",
        example="Paths of all TODO comments found in the repository.",
    )


class LeaderReport(BaseModel):
    """Report returned by the Leader to the user after all tasks are complete."""

    type: Literal["leader_report"] = Field(
        default="leader_report",
        description="Discriminator identifying a LeaderReport object.",
    )
    summary: str = Field(
        ...,
        description="Concise summary of the overall outcome.",
        example="Regression resolved: tearDown no longer runs for skipped tests.",
    )
    details: str = Field(
        ...,
        description="Detailed explanation of the steps taken.",
        example="Applied patch to unittest plugin and verified with pytest --pdb.",
    )
    diff: Optional[str] = Field(
        default=None,
        description="Optional diff of code changes produced by the Executor.",
        example="diff --git a/file.py b/file.py\n- old\n+ new",
    )


LeaderOutput = Annotated[Union[LeaderTaskSpec, LeaderReport], Field(discriminator="type")]

__all__ = [
    "LeaderTaskSpec",
    "LeaderReport",
    "LeaderOutput",
]
