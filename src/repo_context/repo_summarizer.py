# repo_context/repo_summarizer.py
import logging

from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from config import AgentConfig
from models.enums import MessageRole
from repo_context.models import FileSnippet, FileSummary
from utils import LLMFactory

SYSTEM_PROMPT = """
You are a file summarization assistant. Your task is to create a short, concise summary of a file's purpose.

REQUIREMENTS:
- ALWAYS respond with valid JSON matching the format specified below
- Keep summaries to 1 sentence, maximum 10 words
- For code files: describe the main functionality
- For data files: describe the data format or content
- For config files: describe what the file configures
- For documentation files: describe the documentation purpose
- For text files like AUTHORS, LICENSE, README: describe the file's purpose
- Output must be strictly JSON format without extra commentary
"""

USER_PROMPT_TEMPLATE = """Summarize this file:

File path: {file_path}

Content:
{file_content}
"""

ERROR_PROMPT_TEMPLATE = """Your previous response could not be parsed as valid JSON.

Parsing Error:
{error}

Please respond strictly in valid JSON format with only one key "summary" and its sentence summary value.

Example:
"summary": "Configuration for test coverage reporting"

Do not include any extra text or explanations. Try again.
"""

repo_summarizer_config = AgentConfig(SYSTEM_PROMPT=SYSTEM_PROMPT, TEMPERATURE=0.0, MODEL_NAME="qwen-turbo")


class FileSummaryResponse(BaseModel):
    summary: str = Field(
        description="A concise 1 sentence (maximum of 10 words) summary of the file's main purpose and functionality",
        examples=[
            "Python module for HTTP request handling",
            "List of project contributors",
            "Configuration for test coverage reporting",
            "Project license information (MIT)",
        ],
    )


class RepoSummarizer:
    def __init__(self):
        self.llm = LLMFactory.get_llm_from_config(repo_summarizer_config)
        self.parser = JsonOutputParser(pydantic_object=FileSummaryResponse)
        self.base_messages = [
            (MessageRole.SYSTEM.value, f"{SYSTEM_PROMPT}\n\n{{format_instructions}}"),
            (MessageRole.USER.value, USER_PROMPT_TEMPLATE),
        ]

    def summarize_snippet(self, snippet: FileSnippet) -> FileSummary:
        if not snippet.snippet:
            return FileSummary(path=snippet.path, summary="[Empty file]")

        max_content_length = 24000
        content = snippet.snippet
        if len(content) > max_content_length:
            content = content[:max_content_length] + "\n\n[Content truncated due to length...]"

        template_vars = {
            "format_instructions": self.parser.get_format_instructions(),
            "file_path": snippet.path,
            "file_content": content,
        }

        conversation_messages = self.base_messages.copy()
        max_retries = 3
        raw_result = None

        for attempt in range(max_retries + 1):
            try:
                prompt = ChatPromptTemplate.from_messages(conversation_messages)
                chain = prompt | self.llm | self.parser

                raw_result = chain.invoke(template_vars)
                result = FileSummaryResponse(**raw_result)

                return FileSummary(path=snippet.path, summary=result.summary)
            except Exception as e:
                error_msg = str(e).replace("{", "[CURLY_OPEN]").replace("}", "[CURLY_CLOSE]")

                if attempt >= max_retries:
                    logging.error(f"Exceeded retries for file '{snippet.path}'. Final error: {error_msg}")
                    return FileSummary(path=snippet.path, summary="")

                logging.warning(f"Retry {attempt + 1}/{max_retries} for file '{snippet.path}': {error_msg}")

                assistant_response = raw_result if isinstance(raw_result, str) else "[No valid response received]"
                error_prompt = ERROR_PROMPT_TEMPLATE.format(error=error_msg)

                conversation_messages.extend(
                    [
                        (MessageRole.ASSISTANT.value, assistant_response),
                        (MessageRole.USER.value, error_prompt),
                    ]
                )

        # Default fallback (should not typically be reached)
        return FileSummary(path=snippet.path, summary="")
