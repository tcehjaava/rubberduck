from pydantic import TypeAdapter

from rubberduck.autogen.leader_executor.models import (
    SWEBenchVerifiedInstance,
    LeaderTaskSpec,
    LeaderReport,
    ExecutorTaskSpec,
    ExecutorReport,
    LeaderOutput,
    ExecutorOutput,
)


def test_repo_subdir_name():
    data = {
        "repo": "openai/gpt",
        "instance_id": "1",
        "base_commit": "abc",
        "patch": "",
        "test_patch": "",
        "problem_statement": "",
        "hints_text": "",
        "created_at": "",
        "version": "",
        "FAIL_TO_PASS": [],
        "PASS_TO_PASS": [],
        "environment_setup_commit": "def",
    }
    inst = SWEBenchVerifiedInstance(**data)
    assert inst.repo_subdir_name == "gpt"


def test_leader_output_union():
    payload = {"type": "leader_task", "instructions": "Do something"}
    result = TypeAdapter(LeaderOutput).validate_python(payload)
    assert isinstance(result, LeaderTaskSpec)


def test_executor_output_union():
    payload = {
        "type": "executor_report",
        "summary": "done",
        "details": "ok",
    }
    result = TypeAdapter(ExecutorOutput).validate_python(payload)
    assert isinstance(result, ExecutorReport)
