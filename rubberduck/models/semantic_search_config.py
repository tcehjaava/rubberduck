from dataclasses import dataclass
from typing import List


@dataclass
class SemanticSearchConfig:
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 400
    chunk_overlap: int = 50
    top_k_results: int = 5
    collection_prefix: str = "swebench_"
    persist_directory: str = "./chroma_db"
    max_file_size_bytes: int = 1024 * 1024
    excluded_dir_patterns: List[str] = None
    excluded_file_patterns: List[str] = None
    included_extensions: List[str] = None

    def __post_init__(self):
        if self.excluded_dir_patterns is None:
            self.excluded_dir_patterns = [
                "__pycache__",
                ".git",
                ".venv",
                "venv",
                "env",
                ".env",
                "node_modules",
                ".tox",
                ".pytest_cache",
                ".mypy_cache",
                "htmlcov",
                ".coverage",
                "build",
                "dist",
                ".idea",
                ".vscode",
                "*.egg-info",
                ".eggs",
                "site-packages",
                ".ruff_cache",
                ".hypothesis",
                "__pypackages__",
                ".nox",
                ".benchmarks",
                "wheelhouse",
                ".ipynb_checkpoints",
                "docs/_build",
            ]
        if self.excluded_file_patterns is None:
            self.excluded_file_patterns = [
                "*.pyc",
                "*.pyo",
                "*.pyd",
                "*.so",
                "*.dylib",
                "*.dll",
                "*.swp",
                "*.swo",
                "*.swn",
                ".DS_Store",
                "Thumbs.db",
                "*.log",
                "*.sqlite",
                "*.db",
                "*.bak",
                "*.tmp",
                "*.temp",
                "*.cache",
                "*.egg",
                "*.whl",
                "*.tar.gz",
                "*.zip",
                "*.rst",
                "*.md",
                "*.txt",
            ]
        if self.included_extensions is None:
            self.included_extensions = [
                ".py",
                ".pyx",
                ".pyi",
                ".json",
                ".yaml",
                ".yml",
                ".toml",
                ".cfg",
                ".ini",
                ".sh",
                ".bash",
                ".zsh",
                ".sql",
                ".dockerfile",
                ".makefile",
                ".mk",
                ".in",
                ".j2",
                ".jinja2",
            ]
