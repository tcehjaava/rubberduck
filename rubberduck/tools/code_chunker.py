from pathlib import Path
from typing import List

from langchain.text_splitter import Language, RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from loguru import logger

from rubberduck.models.semantic_search_config import SemanticSearchConfig


class CodeChunker:
    def __init__(self, config: SemanticSearchConfig):
        self.config = config

        self.markdown_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.MARKDOWN, chunk_size=config.chunk_size, chunk_overlap=config.chunk_overlap
        )

        self.default_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size, chunk_overlap=config.chunk_overlap
        )

        self.python_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.PYTHON, chunk_size=config.chunk_size, chunk_overlap=config.chunk_overlap
        )

        logger.info(f"CodeChunker initialized with chunk_size={config.chunk_size}, overlap={config.chunk_overlap}")

    def _extract_segment_type(self, segment: str) -> str:
        if not segment:
            return "code"
        first_line = segment.split("\n")[0].strip()
        if first_line.startswith("def "):
            return "function"
        elif first_line.startswith("class "):
            return "class"
        return "code"

    def chunk_python_file(self, file_path: Path, content: str) -> List[Document]:
        return self.python_splitter.create_documents(
            [content],
            metadatas=[
                {
                    "id": f"{file_path.as_posix()}::0",
                    "source": str(file_path),
                    "file_type": file_path.suffix,
                    "segment_type": "code",
                }
            ],
        )

    def chunk_file(self, file_path: Path) -> List[Document]:
        try:
            content = file_path.read_text(encoding="utf-8")
            logger.info(f"Processing {file_path} ({len(content)} chars)")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return []

        if file_path.suffix.lower() in [".py", ".pyw"]:
            return self.chunk_python_file(file_path, content)

        splitter = self.markdown_splitter if file_path.suffix.lower() in [".md", ".markdown"] else self.default_splitter

        chunks = [chunk for chunk in splitter.split_text(content) if chunk.strip()]
        logger.info(f"Split {file_path} into {len(chunks)} chunks using {type(splitter).__name__}")

        documents = []
        for i, chunk in enumerate(chunks):
            metadata = {
                "id": f"{file_path.as_posix()}::{i}",
                "source": str(file_path),
                "file_type": file_path.suffix,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "segment_type": "text",
            }

            documents.append(Document(page_content=chunk, metadata=metadata))

        return documents
