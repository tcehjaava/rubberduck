from rubberduck.autogen.leader_executor.prompts import load_markdown_message


def test_load_markdown_message_substitution():
    content = load_markdown_message("executor_system_message.md", repo_name="myrepo")
    assert "myrepo" in content
