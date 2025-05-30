from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ExecutorTaskSpec(BaseModel):
    reasoning: Optional[str] = Field(
        default=None,
        description=(
            "Detailed rationale and analysis for the approach being taken. ",
            "Make sure the reasoning has at least 100 words.",
        ),
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
