from __future__ import annotations

from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class ExecutorTaskSpec(BaseModel):
    """Task messages produced by the Executor when executing a LeaderTaskSpec."""

    type: Literal["executor_task"] = Field(
        default="executor_task",
        description="Discriminator identifying an ExecutorTaskSpec object.",
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Rationale for the commands that will be executed.",
        example="Listing directories to confirm project layout before searching for TODO markers.",
    )
    commands: List[str] = Field(
        default_factory=list,
        description=(
            "Commands to be executed sequentially. Format each command in a fenced"
            " code block, for example:\n```bash\ncommand\n```."
        ),
        example=[
            "bash -lc 'ls -la /workspace/project/src'",
            "python scripts/scan_for_todo.py",
            "pytest tests/unit/test_sample.py",
        ],
    )


class ExecutorReport(BaseModel):
    """Final report from the Executor sent back to the Leader."""

    type: Literal["executor_report"] = Field(
        default="executor_report",
        description="Discriminator identifying an ExecutorReport object.",
    )
    summary: str = Field(
        ..., description="Summary of the commands executed and results.", example="Executed 2 commands successfully."
    )
    details: str = Field(
        ...,
        description="Detailed output or logs from the commands.",
        example="Found 3 TODO occurrences across two files.",
    )
    diff: Optional[str] = Field(
        default=None,
        description="Optional diff of any changes produced by command execution.",
        example="diff --git a/file.py b/file.py\n- old line\n+ new line",
    )


ExecutorOutput = Annotated[
    Union[ExecutorTaskSpec, ExecutorReport],
    Field(discriminator="type"),
]
