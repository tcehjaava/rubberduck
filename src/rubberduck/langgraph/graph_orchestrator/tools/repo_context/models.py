# repo_context/models.py
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EntryType(str, Enum):
    FILE = "FILE"
    DIRECTORY = "DIRECTORY"


class ContentStatus(str, Enum):
    NONE = "NONE"
    LOADED = "LOADED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


class TreeEntry(BaseModel):
    path: str = Field(..., description="File or directory path")
    entry_type: EntryType = Field(..., description="Type of entry (file or directory)")


class DirectoryTree(BaseModel):
    path: str = Field(..., description="Directory path")
    entry_type: EntryType = Field(EntryType.DIRECTORY, description="Entry type, defaults to DIRECTORY")
    children: List["DirectoryTree"] = Field(default_factory=list, description="Child directories")
    summary: Optional[str] = Field(None, description="Optional summary of directory contents")

    class Config:
        from_attributes = True


DirectoryTree.model_rebuild()


class FileSnippet(BaseModel):
    path: str = Field(..., description="Path to the file")
    snippet: str = Field(..., description="Snippet extracted from file")


class FileSummary(BaseModel):
    path: str = Field(..., description="Path to the file")
    summary: str = Field(..., description="Summary description of file contents")


class RepoFetchRequest(BaseModel):
    repo_name: str = Field(..., description="Name of the repository")
    base_commit: str = Field(..., description="Commit hash or reference")


class SourcegraphResponse(BaseModel):
    data: Dict[str, Any] = Field(default_factory=dict, description="Data returned from Sourcegraph")
    errors: Optional[List[Dict]] = Field(None, description="List of errors returned from Sourcegraph")
