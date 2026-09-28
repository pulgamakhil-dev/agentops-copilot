from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)


logger = get_logger(__name__)


def load_runbooks(runbooks_path: Path):
    """
    Load Markdown troubleshooting runbooks from the configured directory.

    Source metadata is preserved so retrieved chunks can later be traced
    back to the runbook from which they originated.
    """

    if not runbooks_path.exists():
        raise FileNotFoundError(
            f"Runbook directory does not exist: {runbooks_path}"
        )

    loader = DirectoryLoader(
        str(runbooks_path),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True,
    )

    documents = loader.load()

    if not documents:
        raise ValueError(
            f"No Markdown runbooks found in: {runbooks_path}"
        )

    logger.info(
        "Loaded %s runbook documents.",
        len(documents),
    )

    return documents



def split_runbooks(documents):
    """
    Split runbooks by Markdown sections first, preserving headings
    and source metadata. Split oversized sections only when needed.
    """
    settings = get_settings()

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "document"),
            ("##", "section"),
            ("###", "subsection"),
        ],
        strip_headers=False,
    )

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max(settings.rag_chunk_size, 1800),
        chunk_overlap=settings.rag_chunk_overlap,
    )

    chunks = []

    for document in documents:
        sections = markdown_splitter.split_text(
            document.page_content
        )

        for section in sections:
            # Preserve the original filename for citations.
            section.metadata.update(document.metadata)

            # Keep reasonably sized Markdown sections intact.
            if len(section.page_content) <= max(
                settings.rag_chunk_size, 1800
            ):
                chunks.append(section)
            else:
                chunks.extend(
                    text_splitter.split_documents([section])
                )

    logger.info(
        "Created %s section-aware runbook chunks.",
        len(chunks),
    )

    return chunks


def build_vector_store() -> None:
    """
    Build and persist the local FAISS vector index.

    This operation is intended for ingestion/re-indexing rather than
    execution on every user request.
    """

    settings = get_settings()

    documents = load_runbooks(
        Path(settings.runbooks_path)
    )

    chunks = split_runbooks(documents)

    # Embeddings are generated locally. The model name is controlled
    # through environment configuration rather than business logic.
    embeddings = HuggingFaceEmbeddings(
        model_name=settings.embedding_model
    )

    vector_store = FAISS.from_documents(
        documents=chunks,
        embedding=embeddings,
    )

    vector_store_path = Path(
        settings.vector_store_path
    )

    vector_store_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    vector_store.save_local(
        str(vector_store_path)
    )

    logger.info(
        "FAISS vector store saved to %s.",
        vector_store_path,
    )


if __name__ == "__main__":
    configure_logging()
    build_vector_store()