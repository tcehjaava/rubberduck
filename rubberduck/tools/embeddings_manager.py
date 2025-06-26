from typing import List, Optional

import openai
from langchain.embeddings import CacheBackedEmbeddings
from langchain.storage import LocalFileStore
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from rubberduck.models.semantic_search_config import SemanticSearchConfig


class EmbeddingsManager:
    def __init__(self, config: SemanticSearchConfig, instance_id: str):
        self.config = config
        self.instance_id = instance_id
        self.collection_name = f"{config.collection_prefix}{instance_id}"

        # Simple batch size - process N documents at a time
        # With chunk_size of 400, 500 docs should be well under token limits
        self.batch_size = 250

        underlying_embeddings = OpenAIEmbeddings(model=config.embedding_model)

        store = LocalFileStore(f"{config.persist_directory}/embeddings_cache")

        self.embeddings = CacheBackedEmbeddings.from_bytes_store(
            underlying_embeddings, store, namespace=self.collection_name
        )

        self.vectorstore = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=config.persist_directory,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((openai.RateLimitError, openai.APIError, openai.APITimeoutError)),
        reraise=True,
    )
    def _add_documents_with_retry(self, batch: List[Document]):
        self.vectorstore.add_documents(batch)

    def add_documents(self, documents: List[Document]):
        if not documents:
            return

        existing_ids = set(self.vectorstore.get()["ids"])
        new_docs = [doc for doc in documents if doc.metadata["id"] not in existing_ids]

        if not new_docs:
            logger.info("No new documents to add")
            return

        total_docs = len(new_docs)
        for i in range(0, total_docs, self.batch_size):
            batch = new_docs[i : i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (total_docs + self.batch_size - 1) // self.batch_size

            logger.info(f"Processing batch {batch_num}/{total_batches}: {len(batch)} documents")
            self._add_documents_with_retry(batch)

    def search(self, query: str, k: Optional[int] = None) -> List[Document]:
        k = k or self.config.top_k_results
        results_with_scores = self.vectorstore.similarity_search_with_score(query, k=k * 2)

        filtered_results = [doc for doc, score in results_with_scores if score >= 0.7][:k]

        return filtered_results
