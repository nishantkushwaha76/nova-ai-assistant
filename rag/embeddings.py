"""
Gemini embeddings and FAISS vector-store management.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from langchain_core.documents import Document

from langchain_google_genai import (
    GoogleGenerativeAIEmbeddings,
)

from langchain_community.vectorstores import FAISS


# ==========================================================
# PROJECT PATH
# ==========================================================

PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

ENV_FILE = PROJECT_ROOT / ".env"


# ==========================================================
# LOAD ENVIRONMENT
# ==========================================================

load_dotenv(
    dotenv_path=ENV_FILE,
    override=False,
)


# ==========================================================
# CONFIGURATION
# ==========================================================

EMBEDDING_MODEL = (
    "models/gemini-embedding-001"
)

VECTORSTORE_ROOT = (
    PROJECT_ROOT / "vectorstores"
)


# ==========================================================
# API KEY
# ==========================================================

def _get_google_api_key() -> str:

    api_key = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )

    if not api_key:

        raise RuntimeError(
            "Gemini API key is missing. "
            "Add this to the project's .env:\n"
            "GEMINI_API_KEY=YOUR_REAL_GEMINI_API_KEY\n"
            "Then restart FastAPI."
        )

    return api_key.strip()


# ==========================================================
# EMBEDDING MODEL
# ==========================================================

def get_embedding_model():

    api_key = _get_google_api_key()

    print(
        "[rag] Initializing Gemini embeddings: "
        f"{EMBEDDING_MODEL}"
    )

    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=api_key,
        task_type="retrieval_document",
    )


# ==========================================================
# VECTOR STORE PATH
# ==========================================================

def get_vectorstore_path(
    thread_id: str,
) -> Path:

    return (
        VECTORSTORE_ROOT
        / thread_id
    )


# ==========================================================
# CHECK VECTOR STORE
# ==========================================================

def vectorstore_exists(
    thread_id: str,
) -> bool:

    path = get_vectorstore_path(
        thread_id
    )

    return (
        (path / "index.faiss").exists()
        and
        (path / "index.pkl").exists()
    )


# ==========================================================
# CREATE VECTOR STORE
# ==========================================================

def create_vectorstore(
    documents: list[Document],
) -> FAISS:

    if not documents:

        raise ValueError(
            "Cannot create a vector store "
            "from zero documents."
        )

    embedding_model = (
        get_embedding_model()
    )

    print(
        "[rag] Creating FAISS vector store "
        f"from {len(documents)} chunks..."
    )

    vectorstore = FAISS.from_documents(
        documents=documents,
        embedding=embedding_model,
    )

    return vectorstore


# ==========================================================
# SAVE VECTOR STORE
# ==========================================================

def save_vectorstore(
    vectorstore: FAISS,
    thread_id: str,
) -> None:

    path = get_vectorstore_path(
        thread_id
    )

    path.mkdir(
        parents=True,
        exist_ok=True,
    )

    vectorstore.save_local(
        folder_path=str(path)
    )

    print(
        f"[rag] Saved vector store: {path}"
    )


# ==========================================================
# LOAD VECTOR STORE
# ==========================================================

def load_vectorstore(
    thread_id: str,
) -> FAISS:

    if not vectorstore_exists(
        thread_id
    ):

        raise FileNotFoundError(
            "No vector store found for "
            f"thread '{thread_id}'"
        )

    embedding_model = (
        get_embedding_model()
    )

    vectorstore = FAISS.load_local(
        folder_path=str(
            get_vectorstore_path(
                thread_id
            )
        ),
        embeddings=embedding_model,
        allow_dangerous_deserialization=True,
    )

    return vectorstore


# ==========================================================
# ADD DOCUMENTS
# ==========================================================

def add_documents(
    thread_id: str,
    documents: list[Document],
) -> None:

    if not documents:

        raise ValueError(
            "Cannot add zero documents "
            "to the vector store."
        )

    vectorstore = load_vectorstore(
        thread_id
    )

    vectorstore.add_documents(
        documents
    )

    save_vectorstore(
        vectorstore,
        thread_id,
    )