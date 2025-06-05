from typing import List, Literal

from pydantic import BaseModel, Field


class LeaderReviewResponse(BaseModel):
    reasoning: str = Field(description="Detailed analysis of executor performance and decision rationale")

    decision: Literal["RETRY", "SOLVED"] = Field(
        description="Whether to continue with another iteration or if problem is solved"
    )

    what_executor_did_well: List[str] = Field(
        default_factory=list, description="Specific things executor did correctly"
    )

    what_executor_did_poorly: List[str] = Field(default_factory=list, description="Specific mistakes or missed issues")

    recommendations_for_next_run: List[str] = Field(
        default_factory=list, description="Specific, actionable steps for next iteration (for RETRY only)"
    )
