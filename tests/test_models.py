from rubberduck.autogen.leader_executor.models import SWEBenchVerifiedInstance


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
