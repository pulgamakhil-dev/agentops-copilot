
"""
AgentOps Copilot - Runbook Retriever

Features:
- FAISS semantic retrieval
- Section-aware retrieval
- Targeted retrieval for restart and rerun questions
- Complete API timeout procedure retrieval
- Duplicate removal
- Source attribution
"""

import re
from pathlib import Path
from typing import Any

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)


class RunbookRetriever:
    def __init__(self):
        settings = get_settings()

        vector_store_path = Path(
            settings.vector_store_path
        )

        if not vector_store_path.exists():
            raise FileNotFoundError(
                f"FAISS index not found: {vector_store_path}. "
                "Run: python -m app.rag.ingest"
            )

        embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model
        )

        # Load only the trusted index created locally
        # by this project's ingestion pipeline.
        self.vector_store = FAISS.load_local(
            str(vector_store_path),
            embeddings,
            allow_dangerous_deserialization=True,
        )

        logger.info(
            "Loaded runbook FAISS index from %s",
            vector_store_path,
        )

    @staticmethod
    def _document_key(doc) -> tuple[str, str]:
        return (
            str(doc.metadata.get("source", "")),
            doc.page_content,
        )

    @staticmethod
    def _source_name(doc) -> str:
        return Path(
            str(doc.metadata.get("source", "unknown"))
        ).name

    @staticmethod
    def _add_unique(
        documents: list,
        new_documents: list,
    ) -> None:
        """
        Append documents without duplicating
        existing source/content combinations.
        """
        seen = {
            RunbookRetriever._document_key(doc)
            for doc in documents
        }

        for doc in new_documents:
            key = RunbookRetriever._document_key(doc)

            if key not in seen:
                documents.append(doc)
                seen.add(key)

    def _search_section(
        self,
        source: str,
        section: str,
        query: str,
        k: int = 2,
    ) -> list:
        """
        Search for a specific runbook section using
        metadata created by MarkdownHeaderTextSplitter.

        A larger fetch_k allows FAISS to consider
        additional candidates before metadata filtering.
        """
        return self.vector_store.similarity_search(
            query=query,
            k=k,
            filter={
                "section": section,
            },
            fetch_k=100,
        )

    def search(
        self,
        query: str,
        k: int = 4,
    ) -> list[dict[str, Any]]:

        if not query or len(query.strip()) < 3:
            raise ValueError(
                "Search query must contain at least "
                "three characters."
            )

        if not 1 <= k <= 10:
            raise ValueError(
                "k must be between 1 and 10."
            )

        query_lower = query.lower()

        # -------------------------------------------------
        # 1. Standard semantic retrieval
        # -------------------------------------------------

        documents = self.vector_store.similarity_search(
            query=query,
            k=k,
        )

        # -------------------------------------------------
        # 2. Restart / rerun / recovery intent
        # -------------------------------------------------

        restart_intent = bool(
            re.search(
                r"\b("
                r"restart|restarting|"
                r"rerun|rerunning|"
                r"retry|retrying|"
                r"recover|recovery"
                r")\b",
                query_lower,
            )
        )

        if restart_intent:
            remediation_docs = (
                self.vector_store.similarity_search(
                    query=(
                        "Recommended Remediation "
                        "rerun failed pipeline after "
                        "service recovery and approval"
                    ),
                    k=3,
                )
            )

            self._add_unique(
                documents,
                remediation_docs,
            )

        # -------------------------------------------------
        # 3. API timeout procedure intent
        # -------------------------------------------------

        api_timeout_intent = bool(
            re.search(
                r"\bapi[\s_-]*timeouts?\b",
                query_lower,
            )
        )

        procedure_intent = any(
            word in query_lower
            for word in (
                "procedure",
                "handle",
                "handling",
                "remediation",
                "recovery",
                "troubleshoot",
                "investigation",
            )
        )

        if api_timeout_intent:

            sections = [
                (
                    "Investigation Procedure",
                    "API timeout investigation "
                    "HTTP status upstream availability "
                    "latency retry intervals rate limits",
                ),
                (
                    "Recommended Remediation",
                    "API timeout recommended remediation "
                    "upstream recovery controlled retries "
                    "exponential backoff rerun approval",
                ),
                (
                    "Validation After Recovery",
                    "API timeout validation after recovery "
                    "successful API response pipeline "
                    "completion record counts SLA",
                ),
            ]

            for section_name, focused_query in sections:
                section_docs = self._search_section(
                    source="api_timeout.md",
                    section=section_name,
                    query=focused_query,
                    k=2,
                )

                # Only include the intended runbook.
                section_docs = [
                    doc
                    for doc in section_docs
                    if self._source_name(doc)
                    == "api_timeout.md"
                ]

                self._add_unique(
                    documents,
                    section_docs,
                )

        # -------------------------------------------------
        # 4. Format retrieved evidence
        # -------------------------------------------------

        results = []

        for doc in documents:
            results.append(
                {
                    "content": doc.page_content,
                    "source": self._source_name(doc),
                }
            )

        logger.info(
            "Runbook search returned %s passages "
            "for query: %s",
            len(results),
            query,
        )

        return results