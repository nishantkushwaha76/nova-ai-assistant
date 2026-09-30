import asyncio
import os
import tempfile
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from backend_sqlite import (
    create_graph,
    generate_chat_title,
    run_chatbot,
    transcribe_audio,
)

from database import (
    create_thread,
    get_all_threads,
    rename_thread,
    delete_thread,
)

from rag.loader import load_and_split_pdf

from rag.embeddings import (
    vectorstore_exists,
    create_vectorstore,
    add_documents,
    save_vectorstore,
)


app = FastAPI(
    title="AI Voice Assistant API",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    thread_id: str
    message: str


class RenameRequest(BaseModel):
    title: str


def message_to_dict(message):

    if isinstance(message, HumanMessage):
        role = "user"

    elif isinstance(message, AIMessage):
        role = "assistant"

    else:
        return None

    content = (
        message.content
        if isinstance(message.content, str)
        else str(message.content)
    )

    return {
        "role": role,
        "content": content,
    }


# ==========================================================
# HEALTH
# ==========================================================

@app.get("/api/health")
def health():

    return {
        "status": "ok"
    }


# ==========================================================
# CHATS
# ==========================================================

@app.get("/api/chats")
def chats():

    return {
        "chats": get_all_threads()
    }


@app.post("/api/chats")
def new_chat():

    thread_id = str(uuid.uuid4())

    create_thread(thread_id)

    return {
        "id": thread_id,
        "title": "New Chat",
    }


@app.get("/api/chats/{thread_id}")
async def get_chat(thread_id: str):

    try:

        async with AsyncSqliteSaver.from_conn_string(
            "chatbot.db"
        ) as checkpointer:

            chatbot = create_graph(
                checkpointer
            )

            state = await chatbot.aget_state(
                config={
                    "configurable": {
                        "thread_id": thread_id
                    }
                }
            )

            messages = [
                message_to_dict(message)
                for message in state.values.get(
                    "messages",
                    []
                )
            ]

            return {
                "messages": [
                    message
                    for message in messages
                    if message
                ]
            }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@app.patch("/api/chats/{thread_id}")
def rename_chat(
    thread_id: str,
    payload: RenameRequest,
):

    title = payload.title.strip() or "New Chat"

    rename_thread(
        thread_id,
        title,
    )

    return {
        "id": thread_id,
        "title": title,
    }


@app.delete("/api/chats/{thread_id}")
def remove_chat(thread_id: str):

    delete_thread(thread_id)

    return {
        "deleted": True
    }


# ==========================================================
# CHAT
# ==========================================================

@app.post("/api/chat")
async def chat(payload: ChatRequest):

    message = payload.message.strip()

    if not message:

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty",
        )

    threads = {
        item["id"]: item
        for item in get_all_threads()
    }

    if payload.thread_id not in threads:

        create_thread(
            payload.thread_id
        )

        threads = {
            item["id"]: item
            for item in get_all_threads()
        }

    if (
        threads[payload.thread_id]["title"]
        == "New Chat"
    ):

        title = await asyncio.to_thread(
            generate_chat_title,
            message,
        )

        rename_thread(
            payload.thread_id,
            title,
        )

    config = {
        "configurable": {
            "thread_id": payload.thread_id
        }
    }

    try:

        result = await run_chatbot(
            {
                "messages": [
                    HumanMessage(
                        content=message
                    )
                ]
            },
            config=config,
        )

        response = result["messages"][-1].content

        if not isinstance(response, str):
            response = str(response)

        return {
            "thread_id": payload.thread_id,
            "response": response,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


# ==========================================================
# VOICE
# ==========================================================

@app.post("/api/transcribe")
async def transcribe(
    file: UploadFile = File(...)
):

    audio = await file.read()

    if not audio:

        raise HTTPException(
            status_code=400,
            detail="Audio file is empty",
        )

    try:

        text = await asyncio.to_thread(
            transcribe_audio,
            audio,
        )

        return {
            "text": text
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


# ==========================================================
# PDF / RAG
# ==========================================================

@app.post("/api/chats/{thread_id}/pdf")
async def upload_pdf(
    thread_id: str,
    file: UploadFile = File(...),
):

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="No filename was provided",
        )

    if not file.filename.lower().endswith(".pdf"):

        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported",
        )

    create_thread(thread_id)

    tmp_path = None

    try:

        # --------------------------------------------------
        # READ PDF
        # --------------------------------------------------

        content = await file.read()

        if not content:

            raise HTTPException(
                status_code=400,
                detail="PDF file is empty",
            )

        print(
            f"[pdf] Upload received: "
            f"{file.filename} "
            f"({len(content)} bytes)"
        )

        # --------------------------------------------------
        # SAVE TEMP PDF
        # --------------------------------------------------

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf",
        ) as tmp:

            tmp.write(content)

            tmp_path = tmp.name

        print(
            f"[pdf] Temporary file: {tmp_path}"
        )

        # --------------------------------------------------
        # LOAD + SPLIT
        # --------------------------------------------------

        documents = await asyncio.to_thread(
            load_and_split_pdf,
            tmp_path,
        )

        if not documents:

            raise RuntimeError(
                "PDF was loaded but no text chunks "
                "were extracted."
            )

        print(
            f"[pdf] Extracted "
            f"{len(documents)} chunks "
            f"from {file.filename}"
        )

        # --------------------------------------------------
        # VECTOR STORE
        # --------------------------------------------------

        if vectorstore_exists(thread_id):

            print(
                f"[rag] Updating existing vector store: "
                f"{thread_id}"
            )

            await asyncio.to_thread(
                add_documents,
                thread_id,
                documents,
            )

        else:

            print(
                f"[rag] Creating vector store: "
                f"{thread_id}"
            )

            vectorstore = await asyncio.to_thread(
                create_vectorstore,
                documents,
            )

            await asyncio.to_thread(
                save_vectorstore,
                vectorstore,
                thread_id,
            )

        # --------------------------------------------------
        # VERIFY
        # --------------------------------------------------

        if not vectorstore_exists(thread_id):

            raise RuntimeError(
                "Vector store was created but the "
                "FAISS files were not found afterward."
            )

        print(
            f"[rag] PDF indexed successfully "
            f"for thread {thread_id}"
        )

        return {
            "success": True,
            "filename": file.filename,
            "chunks": len(documents),
            "thread_id": thread_id,
        }

    except HTTPException:

        raise

    except Exception as exc:

        print(
            f"[pdf] PDF processing failed: "
            f"{type(exc).__name__}: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"PDF processing failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc

    finally:

        if (
            tmp_path
            and os.path.exists(tmp_path)
        ):

            os.remove(tmp_path)