from __future__ import annotations

from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class ExecutorTaskSpec(BaseModel):
    type: Literal["executor_task"] = Field(
        default="executor_task",
        description="Discriminator identifying an ExecutorTaskSpec object.",
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Detailed rationale and analysis for the approach being taken.",
    )
    operations: List[str] = Field(
        default_factory=list,
        description="Operations to be executed sequentially as code blocks.",
        example=[
            """```python
if unittest and call.excinfo and call.excinfo.errisinstance(unittest.SkipTest):
    call2 = CallInfo.from_call(
        lambda: pytest.skip(str(call.excinfo.value)), call.when
    )
    call.excinfo = call2.excinfo
```""",
            """```bash
grep -C 5 "_explicit_tearDown" /workspace/pytest/src/_pytest/unittest.py
```""",
        ],
    )


class ExecutorReport(BaseModel):
    type: Literal["executor_report"] = Field(
        default="executor_report",
        description="Discriminator identifying an ExecutorReport object.",
    )
    status: Literal["success", "failure", "partial", "terminated"] = Field(
        ...,
        description="Overall status of the task execution.",
    )
    findings: List[str] = Field(
        default_factory=list,
        description="Key discoveries or insights from the task execution.",
    )
    execution_details: List[str] = Field(
        default_factory=list,
        description="Detailed results from each operation that was executed.",
    )
    code_changes: Optional[str] = Field(
        default=None,
        description="Diff of any code modifications made.",
    )
    termination_reason: Optional[str] = Field(
        default=None,
        description="Reason for early termination, if applicable.",
    )


ExecutorOutput = Annotated[
    Union[ExecutorTaskSpec, ExecutorReport],
    Field(discriminator="type"),
]
