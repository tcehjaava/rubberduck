# config/global_config.py

import os

from dotenv import load_dotenv

from config.config_models import GlobalConfig

load_dotenv()

GLOBAL_CONFIG = GlobalConfig(
    ANTHROPIC_API_KEY=os.getenv("ANTHROPIC_API_KEY"),
    GEMINI_API_KEY=os.getenv("GEMINI_API_KEY"),
    DEEPSEEK_API_KEY=os.getenv("DEEPSEEK_API_KEY"),
    OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
    QWEN_API_KEY=os.getenv("QWEN_API_KEY"),
    # pytest-dev/pytest is the easiest repo to start with
    INSTANCE_ID="pytest-dev__pytest-10051",
    MODEL_NAME="qwen-max",
    SOURCEGRAPH_ENDPOINT="https://codeon.sourcegraph.app/.api/",
    SOURCEGRAPH_GQL_URL="https://codeon.sourcegraph.app/.api/graphql",
    SOURCEGRAPH_API_TOKEN=os.getenv("SOURCEGRAPH_API_TOKEN"),
)
