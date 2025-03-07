# src/utils/llm_factory.py

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from config.config_models import AgentConfig
from config.global_config import GLOBAL_CONFIG


class LLMFactory:

    @staticmethod
    def get_llm_from_config(config: AgentConfig):
        model_name = config.MODEL_NAME or GLOBAL_CONFIG.MODEL_NAME
        temperature = config.TEMPERATURE if config.TEMPERATURE is not None else 0.0

        if model_name.startswith("gpt") or model_name.startswith("o3-"):
            return ChatOpenAI(model=model_name, temperature=temperature, openai_api_key=GLOBAL_CONFIG.OPENAI_API_KEY)
        elif model_name.startswith("gemini"):
            return ChatGoogleGenerativeAI(
                model=model_name, temperature=temperature, google_api_key=GLOBAL_CONFIG.GEMINI_API_KEY
            )
        elif model_name.startswith("claude"):
            return ChatAnthropic(
                model=model_name, temperature=temperature, anthropic_api_key=GLOBAL_CONFIG.ANTHROPIC_API_KEY
            )
        elif model_name.startswith("qwen"):
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                openai_api_key=GLOBAL_CONFIG.QWEN_API_KEY,
                base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            )
        elif model_name.startswith("deepseek"):
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                openai_api_key=GLOBAL_CONFIG.DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com",
            )
        else:
            raise ValueError(f"Unsupported model: {model_name}")
