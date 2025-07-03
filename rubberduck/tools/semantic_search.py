import io
import json
import shlex
import tarfile
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional

from docker.models.containers import Container
from langchain_core.documents import Document
from loguru import logger

from rubberduck.models.semantic_search_config import SemanticSearchConfig
from rubberduck.tools.code_chunker import CodeChunker
from rubberduck.tools.container_manager import run_script_in_container
from rubberduck.tools.embeddings_manager import EmbeddingsManager


class SemanticSearch:
    def __init__(self, config: SemanticSearchConfig, instance_id: str, container: Container):
        self.config = config
        self.instance_id = instance_id
        self.container = container

        self.embeddings_manager = EmbeddingsManager(config, instance_id)
        self.chunker = CodeChunker(config)

        logger.info(f"SemanticSearch initialized for instance {instance_id}")

    def _get_index_state_file(self) -> Path:
        state_dir = Path(self.config.persist_directory) / "index_states"
        state_dir.mkdir(exist_ok=True)
        return state_dir / f"{self.instance_id}.json"

    def _is_indexed(self) -> bool:
        state_file = self._get_index_state_file()

        if not state_file.exists():
            return False

        try:
            with open(state_file, "r") as f:
                state = json.load(f)
                return state.get("indexed", False)
        except Exception:
            return False

    def _mark_as_indexed(self, file_count: int) -> None:
        state_file = self._get_index_state_file()

        state = {
            "indexed": True,
            "indexed_at": time.time(),
            "file_count": file_count,
            "instance_id": self.instance_id,
        }

        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

    def _get_files_from_container(self) -> List[str]:
        python_script = f"""
import os
import fnmatch
import json

excluded_dirs = {json.dumps(self.config.excluded_dir_patterns)}
excluded_files = {json.dumps(self.config.excluded_file_patterns)}
included_exts = {json.dumps(self.config.included_extensions)}
max_size = {self.config.max_file_size_bytes}

files = []
for root, dirs, filenames in os.walk('/testbed'):
    # Remove excluded directories from traversal
    dirs[:] = [d for d in dirs if not any(
        fnmatch.fnmatch(d, pattern) for pattern in excluded_dirs
    )]

    for filename in filenames:
        filepath = os.path.join(root, filename)

        try:
            if os.path.getsize(filepath) >= max_size:
                continue
        except (OSError, IOError):
            continue

        # Check excluded patterns
        if any(fnmatch.fnmatch(filename, pattern) for pattern in excluded_files):
            continue

        # Check included extensions
        if any(filename.lower().endswith(ext.lower()) for ext in included_exts):
            files.append(filepath)

print(json.dumps(files))
"""
        exit_code, output = run_script_in_container(self.container, f"python3 -c {shlex.quote(python_script)}")

        if exit_code != 0:
            raise RuntimeError(f"Failed to list files: {output}")

        return json.loads(output.strip())

    def _read_file_from_container(self, file_path: str) -> str:
        try:
            file_path.encode("utf-8")
        except UnicodeEncodeError:
            raise RuntimeError(f"INVALID_ENCODING: Cannot process file with invalid UTF-8 path: {file_path}")

        try:
            bits, stat = self.container.get_archive(file_path)

            file_data = io.BytesIO()
            for chunk in bits:
                file_data.write(chunk)
            file_data.seek(0)

            with tarfile.open(fileobj=file_data) as tar:
                for member in tar.getmembers():
                    if member.isfile():
                        file_obj = tar.extractfile(member)
                        if file_obj:
                            try:
                                content = file_obj.read().decode("utf-8")
                                return content
                            except UnicodeDecodeError:
                                # File contains binary data, skip it
                                raise RuntimeError(f"BINARY_FILE: {file_path}")

            raise RuntimeError(f"Could not extract {file_path} from archive")

        except Exception as e:
            if "Could not find the file" in str(e) or "no such file" in str(e).lower():
                raise RuntimeError(f"FILE_NOT_FOUND: {file_path}")
            raise RuntimeError(f"Failed to read {file_path}: {e}")

    def _process_file_batch(self, file_paths: List[str], temp_dir: Path) -> List[Document]:
        documents = []

        for file_path in file_paths:
            try:
                content = self._read_file_from_container(file_path)
            except RuntimeError as e:
                if "FILE_NOT_FOUND" in str(e):
                    logger.info(f"Skipping non-existent file: {file_path}")
                    continue
                elif "BINARY_FILE" in str(e):
                    logger.info(f"Skipping binary file: {file_path}")
                    continue
                elif "INVALID_ENCODING" in str(e):
                    logger.warning("Skipping file with invalid UTF-8 encoding in path")
                    continue
                raise

            path_obj = Path(file_path)
            file_hash = str(abs(hash(file_path)))
            temp_subdir = temp_dir / file_hash
            temp_subdir.mkdir(exist_ok=True)

            temp_path = temp_subdir / path_obj.name
            temp_path.write_text(content, encoding="utf-8")

            file_documents = self.chunker.chunk_file(temp_path)
            for doc in file_documents:
                doc.metadata["source"] = file_path
                doc.metadata["id"] = doc.metadata["id"].replace(str(temp_path), file_path)

            documents.extend(file_documents)

            temp_path.unlink()
            try:
                temp_subdir.rmdir()
            except OSError:
                pass

        return documents

    def index_codebase(self) -> None:
        if self._is_indexed():
            logger.info("Codebase already indexed, skipping")
            return

        logger.info("Starting codebase indexing from container...")

        files = self._get_files_from_container()
        batch_size = 100
        total_documents = 0

        with tempfile.TemporaryDirectory(prefix=f"semantic_search_{self.instance_id}_") as temp_dir:
            temp_dir_path = Path(temp_dir)

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []

                for i in range(0, len(files), batch_size):
                    batch = files[i : i + batch_size]
                    future = executor.submit(self._process_file_batch, batch, temp_dir_path)
                    futures.append(future)

                for i, future in enumerate(as_completed(futures)):
                    documents = future.result()
                    if documents:
                        logger.info(f"Batch {i+1}/{len(futures)}: Adding {len(documents)} documents")
                        self.embeddings_manager.add_documents(documents)
                        total_documents += len(documents)

        self._mark_as_indexed(len(files))
        logger.info(f"Indexing complete. Processed {len(files)} files, created {total_documents} documents")

    def search(self, query: str, k: Optional[int] = None) -> str:
        logger.info(f"Searching for: {query}")
        results = self.embeddings_manager.search(query, k)
        logger.info(f"Found {len(results)} results")

        if not results:
            return "No relevant code found for the query."

        formatted = [f"Found {len(results)} relevant code sections:\n"]

        for i, doc in enumerate(results, 1):
            metadata = doc.metadata
            source = metadata.get("source", "unknown")
            segment_type = metadata.get("segment_type", "code")

            formatted.append(f"{i}. [{source}] ({segment_type})")
            formatted.append(doc.page_content)
            formatted.append("-" * 80)

        return "\n".join(formatted)
