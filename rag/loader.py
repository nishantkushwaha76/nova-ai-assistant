"""
PDF loading and chunking for Nova RAG.
"""

from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
)


# ==========================================================
# CONFIGURATION
# ==========================================================

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 250


# ==========================================================
# LOAD PDF
# ==========================================================

def load_pdf(
    pdf_path: str,
) -> list[Document]:

    pdf_file = Path(pdf_path)

    if not pdf_file.exists():

        raise FileNotFoundError(
            f"PDF not found: {pdf_file}"
        )

    print(
        f"[pdf] Loading PDF: {pdf_file}"
    )

    documents = PyPDFLoader(
        str(pdf_file)
    ).load()

    if not documents:

        raise ValueError(
            "PyPDFLoader returned no pages."
        )

    # Remove completely empty pages
    documents = [
        document
        for document in documents
        if (
            document.page_content
            and document.page_content.strip()
        )
    ]

    if not documents:

        raise ValueError(
            "The PDF contains no extractable text. "
            "If this is a scanned/image-only PDF, "
            "OCR is required."
        )

    print(
        f"[pdf] Loaded {len(documents)} "
        f"text pages"
    )

    return documents


# ==========================================================
# SPLIT DOCUMENTS
# ==========================================================

def split_documents(
    documents: list[Document],
) -> list[Document]:

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        is_separator_regex=False,
    )

    chunks = splitter.split_documents(
        documents
    )

    chunks = [
        chunk
        for chunk in chunks
        if (
            chunk.page_content
            and chunk.page_content.strip()
        )
    ]

    print(
        f"[pdf] Created {len(chunks)} chunks"
    )

    return chunks


# ==========================================================
# LOAD + SPLIT
# ==========================================================

def load_and_split_pdf(
    pdf_path: str,
) -> list[Document]:

    documents = load_pdf(
        pdf_path
    )

    chunks = split_documents(
        documents
    )

    if not chunks:

        raise ValueError(
            "PDF text was extracted, "
            "but no chunks were produced."
        )

    return chunks