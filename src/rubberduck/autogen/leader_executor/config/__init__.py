import os

from dotenv import load_dotenv

from .load_llm_config import load_llm_config

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

__all__: list[str] = ["load_llm_config"]
