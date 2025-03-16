# repo_context/repo_fetcher.py

import logging
import os
from typing import Any, Dict, List, Optional

import requests
from joblib import delayed

from config import GLOBAL_CONFIG
from repo_context.models import EntryType, FileSnippet, RepoFetchRequest, TreeEntry
from repo_context.repo_summarizer import RepoSummarizer
from repo_context.storage_manager import StorageManager


class RepoFetcher:
    HEADERS = {
        "Authorization": f"token {GLOBAL_CONFIG.SOURCEGRAPH_API_TOKEN}",
        "Content-Type": "application/json",
    }

    BINARY_EXTENSIONS = {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".ico",
        ".webp",
        ".mp3",
        ".mp4",
        ".avi",
        ".mov",
        ".flv",
        ".wmv",
        ".zip",
        ".tar",
        ".gz",
        ".rar",
        ".7z",
        ".pyc",
        ".jar",
        ".war",
        ".ear",
        ".class",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
    }

    MAX_FILE_SIZE = 1024 * 1024

    @staticmethod
    def _get_nested_value(data: Dict, keys: List[str], default: Any = None) -> Any:
        current = data
        for key in keys:
            if not current or not isinstance(current, dict) or key not in current:
                return default
            current = current[key]
        return current

    @staticmethod
    def _fetch_tree_entries(repo_name: str, commit: str, path: str) -> List[TreeEntry]:
        query = """
        query ($repo: String!, $commit: String!, $path: String!) {
          repository(name: $repo) {
            commit(rev: $commit) {
              tree(path: $path) {
                entries {
                  path
                  isDirectory
                }
              }
            }
          }
        }
        """
        variables = {"repo": repo_name, "commit": commit, "path": path}

        try:
            response = requests.post(
                GLOBAL_CONFIG.SOURCEGRAPH_GQL_URL,
                json={"query": query, "variables": variables},
                headers=RepoFetcher.HEADERS,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            entries = RepoFetcher._get_nested_value(data, ["data", "repository", "commit", "tree", "entries"], [])

            if not entries:
                logging.warning(f"No entries found for path: {path}")
                return []

            return [
                TreeEntry(path=e["path"], entry_type=EntryType.DIRECTORY if e["isDirectory"] else EntryType.FILE)
                for e in entries
            ]
        except Exception as e:
            logging.error(f"Error fetching tree at path '{path}': {e}")
            return []

    @staticmethod
    def _check_file_size(repo_name: str, commit: str, file_path: str) -> Optional[int]:
        query = """
        query ($repo: String!, $commit: String!, $path: String!) {
          repository(name: $repo) {
            commit(rev: $commit) {
              file(path: $path) {
                byteSize
              }
            }
          }
        }
        """
        variables = {"repo": repo_name, "commit": commit, "path": file_path}

        try:
            response = requests.post(
                GLOBAL_CONFIG.SOURCEGRAPH_GQL_URL,
                json={"query": query, "variables": variables},
                headers=RepoFetcher.HEADERS,
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()

            byte_size = RepoFetcher._get_nested_value(data, ["data", "repository", "commit", "file", "byteSize"], None)

            if byte_size is None:
                logging.warning(f"Could not retrieve size for file: {file_path}")

            return byte_size
        except Exception as e:
            logging.error(f"Error checking file size for '{file_path}': {e}")
            return None

    @staticmethod
    def _should_process_file(file_path: str, file_size: Optional[int]) -> bool:
        _, ext = os.path.splitext(file_path.lower())
        if ext in RepoFetcher.BINARY_EXTENSIONS:
            logging.info(f"Skipping binary file: {file_path}")
            return False

        if file_size and file_size > RepoFetcher.MAX_FILE_SIZE:
            logging.info(f"Skipping large file: {file_path} ({file_size} bytes)")
            return False

        return True

    @staticmethod
    def _fetch_file_snippet(repo_name: str, commit: str, file_path: str) -> FileSnippet:
        file_size = RepoFetcher._check_file_size(repo_name, commit, file_path)
        if not RepoFetcher._should_process_file(file_path, file_size):
            return FileSnippet(path=file_path, snippet="")

        query = """
        query ($repo: String!, $commit: String!, $path: String!) {
          repository(name: $repo) {
            commit(rev: $commit) {
              file(path: $path) {
                content
              }
            }
          }
        }
        """
        variables = {"repo": repo_name, "commit": commit, "path": file_path}

        try:
            response = requests.post(
                GLOBAL_CONFIG.SOURCEGRAPH_GQL_URL,
                json={"query": query, "variables": variables},
                headers=RepoFetcher.HEADERS,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            content = RepoFetcher._get_nested_value(data, ["data", "repository", "commit", "file", "content"], None)

            if content is None:
                logging.warning(f"No content found for file: {file_path}")
                return FileSnippet(path=file_path, snippet="")

            if content and len(content) > 10240:
                content = content[:10240] + "\n\n... [content truncated due to size] ..."

            return FileSnippet(path=file_path, snippet=content if content else "")
        except Exception as e:
            logging.error(f"Error fetching snippet for file '{file_path}': {e}")
            return FileSnippet(path=file_path, snippet="")

    @classmethod
    def _process_directory(cls, request: RepoFetchRequest, path: str, parent_id: Optional[str] = None):
        current_id = f"{request.repo_name}:{request.base_commit}:{path}" if path else None

        if path:
            StorageManager.store_entry(
                request.repo_name, request.base_commit, path, EntryType.DIRECTORY, parent_id=parent_id
            )

        entries = cls._fetch_tree_entries(request.repo_name, request.base_commit, path)

        dirs = [e for e in entries if e.entry_type == EntryType.DIRECTORY]
        files = [e for e in entries if e.entry_type == EntryType.FILE]

        for file_entry in files:
            StorageManager.store_entry(
                request.repo_name, request.base_commit, file_entry.path, EntryType.FILE, parent_id=current_id
            )

        return dirs, current_id

    @classmethod
    def fetch_and_store_repo_structure(cls, request: RepoFetchRequest):
        logging.info(f"Fetching structure for {request.repo_name}@{request.base_commit}")

        dirs_to_process = [("", None)]  # (path, parent_id)

        while dirs_to_process:
            batch = dirs_to_process[:100]  # Process in batches to avoid memory issues
            dirs_to_process = dirs_to_process[100:]

            def process_single_dir(dir_info):
                path, parent_id = dir_info
                subdirs, current_id = cls._process_directory(request, path, parent_id)
                return [(subdir.path, current_id) for subdir in subdirs]

            results = GLOBAL_CONFIG.PARALLEL_EXECUTOR(delayed(process_single_dir)(dir_info) for dir_info in batch)

            for subdir_list in results:
                dirs_to_process.extend(subdir_list)

    @classmethod
    def _check_file_sizes_batch(cls, request: RepoFetchRequest, file_paths: List[str], batch_size: int = 50):
        file_sizes = {}

        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i : i + batch_size]

            def check_size(path):
                size = cls._check_file_size(request.repo_name, request.base_commit, path)
                return path, size

            results = GLOBAL_CONFIG.PARALLEL_EXECUTOR(delayed(check_size)(path) for path in batch)

            for path, size in results:
                file_sizes[path] = size

        return file_sizes

    @classmethod
    def fetch_summarize_and_store_snippets(cls, request: RepoFetchRequest):
        file_paths = StorageManager.load_file_paths(request.repo_name, request.base_commit)
        logging.info(f"Found {len(file_paths)} files to process for {request.repo_name}@{request.base_commit}")

        file_sizes = cls._check_file_sizes_batch(request, file_paths)
        processable_files = [path for path in file_paths if cls._should_process_file(path, file_sizes.get(path))]

        logging.info(f"Processing {len(processable_files)} of {len(file_paths)} files (skipping binary/large files)")

        repo_summarizer = RepoSummarizer()

        def process_file(file_path):
            try:
                snippet = cls._fetch_file_snippet(request.repo_name, request.base_commit, file_path)

                if not snippet.snippet:
                    return

                summary = repo_summarizer.summarize_snippet(snippet)
                if summary and summary.summary:
                    StorageManager.store_summary(request.repo_name, request.base_commit, file_path, summary.summary)
                else:
                    logging.warning(f"Failed to generate summary for file: {file_path}")
            except Exception as e:
                logging.error(f"Error processing file '{file_path}': {e}")

        GLOBAL_CONFIG.PARALLEL_EXECUTOR(delayed(process_file)(path) for path in processable_files[:20])
        logging.info(f"Completed processing files for {request.repo_name}@{request.base_commit}")

    @classmethod
    def fetch_repo_full(cls, repo_name: str, commit: str, refresh: bool = False):
        request = RepoFetchRequest(repo_name=repo_name, base_commit=commit)

        if not refresh:
            root_entries = StorageManager.get_root_entries(repo_name, commit)
            if root_entries:
                logging.info(f"Using existing data for {repo_name}@{commit}")
                return StorageManager.build_directory_tree(repo_name, commit)

        cls.fetch_and_store_repo_structure(request)
        cls.fetch_summarize_and_store_snippets(request)

        return StorageManager.build_directory_tree(repo_name, commit)
