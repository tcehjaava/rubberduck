from typing import List

from pydantic import BaseModel, Field


class SWEBenchVerifiedInstance(BaseModel):
    repo: str
    instance_id: str
    base_commit: str
    patch: str
    test_patch: str
    problem_statement: str
    hints_text: str
    created_at: str
    version: str
    fail_to_pass: List[str] = Field(..., alias="FAIL_TO_PASS")
    pass_to_pass: List[str] = Field(..., alias="PASS_TO_PASS")
    environment_setup_commit: str

    @property
    def repo_subdir_name(self) -> str:
        return self.repo.rstrip("/").split("/")[-1]

    class Config:
        populate_by_name = True
        frozen = True
