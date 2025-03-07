# src/models/output_models.py

from typing import List, Optional

from pydantic import BaseModel, Field

from models import QueryType


class ExpectedBehavior(BaseModel):
    summary: str = Field(
        description="Short, high-level summary of the expected outcome.",
        example="The field value should be retrieved as a plain string or integer instead of an enum.",
    )
    details: List[str] = Field(
        default_factory=list,
        description="More detailed aspects or bullet points of the expected behavior.",
        example=[
            "Accessing my_object.my_str_value returns a normal string 'first'.",
            "No enum references should appear when using __str__ on the field value.",
        ],
    )


class ActualBehavior(BaseModel):
    summary: str = Field(
        description="Short summary describing what actually happens.",
        example="The field value is stored and retrieved as an enum, causing type mismatches.",
    )
    details: List[str] = Field(
        default_factory=list,
        description="More detailed aspects or bullet points of the actual/incorrect behavior.",
        example=[
            "Instead of 'first', the system returns 'MyChoice.FIRST_CHOICE'.",
            "Test assertion fails due to type mismatch.",
        ],
    )


class KnowledgeUsed(BaseModel):
    sources: List[str] = Field(
        default_factory=list,
        description="List of sources from the input that contributed to the extraction.",
        example=["Raw text provided by the user", "Base commit SHA", "Repository name"],
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="Any inferences or guesses about missing data or context made during extraction.",
        example=["Assumed no environment details were provided", "Assumed Django version not specified"],
    )
    external_knowledge: bool = Field(
        default=False,
        description="Indicates whether external knowledge or context (beyond the user input) was used.",
        example=False,
    )


class IssueData(BaseModel):
    """
    Main container for extracted issue information.
    All fields must conform to the schema definitions below.
    """

    repo_name: str = Field(description="Repository name in 'owner/repo' format.", example="django/django")
    issue_title: str = Field(
        description="A short descriptive title for the issue.",
        example="The value of a TextChoices/IntegerChoices field has a differing type",
    )
    problem_type: str = Field(
        description="Type of problem. Must be one of: 'Bug', 'Feature', or 'Documentation'.", example="Bug"
    )
    description: str = Field(
        description="Concise summary describing the primary concern/issue.",
        example="When using TextChoices for a CharField, the returned field value is an enum rather than a string.",
    )
    raw_text: str = Field(
        description=(
            "Full, unstructured text or original problem statement describing the issue",
            " (e.g., logs, error messages).",
        ),
        example="Traceback (most recent call last)...\nAssertionError: 'MyChoice.FIRST_CHOICE' != 'first'",
    )
    steps_to_reproduce: List[str] = Field(
        default_factory=list,
        description="Ordered list of steps to replicate the issue.",
        example=["Create a Django model with TextChoices on a CharField.", "Run the tests verifying the field's type."],
    )
    expected_behavior: ExpectedBehavior = Field(
        description="Model describing the ideal or intended behavior of the system."
    )
    actual_behavior: ActualBehavior = Field(
        description="Model describing the currently observed or unintended behavior."
    )
    files_involved: List[str] = Field(
        default_factory=list,
        description="List of file paths or filenames relevant to the issue.",
        example=["testing/pkg/models.py", "testing/tests.py"],
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="Search terms used to locate relevant code in the repository for fixing the issue.",
        example=["TextChoices", "IntegerChoices", "enum", "CharField", "tests"],
    )
    environment_info: List[str] = Field(
        default_factory=list,
        description="Relevant environment or system setup details (OS, Python, framework versions, etc.).",
        example=["OS: Ubuntu 20.04", "Python: 3.8.10", "Django: 3.2.7"],
    )
    additional_links: List[str] = Field(
        default_factory=list,
        description="Any external links, references, or related resources.",
        example=["https://github.com/django/django/issues/12345", "https://yapb.in/exUE.png"],
    )
    base_commit: Optional[str] = Field(
        None, description="SHA of the relevant commit, if provided.", example="fc2b1cc926e34041953738e58fa6ad3053059b22"
    )
    knowledge_used: KnowledgeUsed = Field(
        default_factory=KnowledgeUsed, description="Information about what was used to produce this extraction."
    )


class SearchQuery(BaseModel):
    query_type: QueryType = Field(description="Type of Sourcegraph query to execute")
    query: str = Field(description="The Sourcegraph query string")
    rationale: str = Field(description="Explanation of why this query is relevant")
