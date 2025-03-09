# src/models/enums.py

from enum import Enum


class FileType(str, Enum):
    """Types of files that might be relevant to the issue."""

    IMPLEMENTATION = "implementation"
    TEST = "test"
    DOCUMENTATION = "documentation"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


class FileRelevanceLevel(str, Enum):
    """Classification of how relevant a file is to solving the issue."""

    CRITICAL = "critical"
    RELEVANT = "relevant"
    REFERENCE = "reference"


class QueryType(str, Enum):
    RELEVANT_FILES = "relevant_files"
    FILE_CONTENT = "file_content"


class NextStep(str, Enum):
    NEXT = "next"
    END = "end"


class MessageRole(str, Enum):
    """Roles for messages in conversation with LLM."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class OrchestratorAction(str, Enum):
    RELEVANCE_SEARCH = "RELEVANCE_SEARCH"  # For code/relevance search tasks
    END = "END"  # To terminate the workflow
    # Future actions can be added here as needed
