from rubberduck.autogen.leader_executor.config import load_llm_config


def test_load_llm_config_default_executor():
    config = load_llm_config("default_executor")
    assert isinstance(config, list)
    assert config
    assert all("model" in entry for entry in config)
