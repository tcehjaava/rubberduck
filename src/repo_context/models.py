# repo_context/models.py
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class EntryType(str, Enum):
    FILE = "file"
    DIRECTORY = "directory"


class TreeEntry(BaseModel):
    path: str
    entry_type: EntryType


class DirectoryTree(BaseModel):
    path: str
    entry_type: EntryType = EntryType.DIRECTORY
    children: List["DirectoryTree"] = Field(default_factory=list)
    summary: Optional[str] = None

    class Config:
        from_attributes = True


DirectoryTree.model_rebuild()


class FileSnippet(BaseModel):
    path: str
    snippet: str


class FileSummary(BaseModel):
    path: str
    summary: str


class RepoFetchRequest(BaseModel):
    repo_name: str
    base_commit: str


class SourcegraphResponse(BaseModel):
    data: Dict = Field(default_factory=dict)
    errors: Optional[List[Dict]] = None
