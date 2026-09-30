# ============================================================
# backend_sqlite.py
# Nova AI Assistant
# Groq + LangGraph + MCP + RAG + SQLite + Voice
# ============================================================


# ==================== 1. IMPORTS ====================

import os
import asyncio
import aiosqlite
import traceback

from typing import Annotated, TypedDict

from dotenv import load_dotenv
from groq import Groq

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    SystemMessage,
)

from langchain_core.runnables import RunnableConfig
from langchain_groq import ChatGroq

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from langgraph.graph import (
    END,
    START,
    StateGraph,
)

from langgraph.graph.message import add_messages

from langgraph.prebuilt import (
    ToolNode,
    tools_condition,
)

from guardrails import (
    check_input,
    check_output,
)

from mcp_client import get_mcp_tools

from rag.prompts import SYSTEM_PROMPT

from rag.embeddings import (
    load_vectorstore,
    vectorstore_exists,
)


# ==================== 2. ENVIRONMENT ====================

load_dotenv()


# ============================================================
# 3. VOICE / SPEECH TO TEXT
# ============================================================

def transcribe_audio(audio_bytes: bytes) -> str:
    """
    Convert audio bytes into text using Groq Whisper.
    """

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured."
        )

    client = Groq(
        api_key=api_key
    )

    transcription = client.audio.transcriptions.create(
        file=(
            "recording.wav",
            audio_bytes
        ),
        model="whisper-large-v3-turbo",
        response_format="json",
        temperature=0.0,
    )

    return transcription.text.strip()


# ============================================================
# 4. LLM
# ============================================================

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.7,
    streaming=True,
)


# ============================================================
# 5. MCP SETUP
# ============================================================

# IMPORTANT:
#
# Do NOT call:
#
# asyncio.run(get_mcp_tools())
#
# at module level.
#
# FastAPI/Uvicorn already has an asyncio event loop.
#
# MCP tools are loaded asynchronously from run_chatbot().

MCP_TOOLS = []

llm_with_tools = llm

_mcp_initialized = False

_mcp_initializing = False

_mcp_lock = asyncio.Lock()


async def initialize_mcp_tools():
    """
    Load Gmail and Google Calendar MCP tools.

    This runs inside the existing asyncio event loop.
    """

    global MCP_TOOLS
    global llm_with_tools
    global _mcp_initialized
    global _mcp_initializing

    if _mcp_initialized:
        return

    async with _mcp_lock:

        if _mcp_initialized:
            return

        if _mcp_initializing:
            return

        _mcp_initializing = True

        try:

            print(
                "[mcp] Loading MCP tools..."
            )

            tools = await get_mcp_tools()

            MCP_TOOLS = tools or []

            if MCP_TOOLS:

                llm_with_tools = llm.bind_tools(
                    MCP_TOOLS
                )

                _mcp_initialized = True

                print(
                    f"[mcp] Loaded {len(MCP_TOOLS)} MCP tools"
                )

                for tool in MCP_TOOLS:

                    tool_name = getattr(
                        tool,
                        "name",
                        str(tool),
                    )

                    print(
                        f"[mcp] Tool available: {tool_name}"
                    )

            else:

                print(
                    "[mcp] No MCP tools were returned."
                )

                MCP_TOOLS = []

                llm_with_tools = llm

                _mcp_initialized = False

        except Exception as error:

            print(
                f"[mcp] Could not load MCP tools: {error}"
            )

            traceback.print_exc()

            MCP_TOOLS = []

            llm_with_tools = llm

            _mcp_initialized = False

        finally:

            _mcp_initializing = False


# ============================================================
# 6. CHAT STATE
# ============================================================

class ChatState(TypedDict):

    messages: Annotated[
        list[BaseMessage],
        add_messages
    ]

    context: str

    blocked: bool

    block_reason: str


# ============================================================
# 7. INPUT GUARDRAIL
# ============================================================

def guardrail_input_node(
    state: ChatState,
    config: RunnableConfig,
) -> ChatState:

    thread_id = config[
        "configurable"
    ][
        "thread_id"
    ]

    last_message = state[
        "messages"
    ][-1]

    result = check_input(
        thread_id,
        last_message.content,
    )

    if not result.allowed:

        return {
            "blocked": True,
            "block_reason": result.reason,
        }

    last_message.content = (
        result.sanitized_text
    )

    return {
        "blocked": False,
        "block_reason": "",
    }


# ============================================================
# 8. GEMINI QUERY EMBEDDING
# ============================================================

EMBEDDING_MODEL = "models/gemini-embedding-001"


def get_query_embedding_model():
    """
    Create the Gemini embedding model specifically
    for retrieval queries.

    Documents are indexed using RETRIEVAL_DOCUMENT.
    User questions are embedded using RETRIEVAL_QUERY.
    """

    api_key = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )

    if not api_key:

        raise RuntimeError(
            "GEMINI_API_KEY or GOOGLE_API_KEY "
            "is not configured."
        )

    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        task_type="retrieval_query",
        google_api_key=api_key,
    )


# ============================================================
# 9. RAG RETRIEVAL
# ============================================================

def retrieve_node(
    state: ChatState,
    config: RunnableConfig,
) -> ChatState:

    if state.get("blocked"):

        return {
            "context": ""
        }

    thread_id = config[
        "configurable"
    ][
        "thread_id"
    ]

    query = state[
        "messages"
    ][-1].content

    print(
        f"[rag] Retrieval request "
        f"thread={thread_id}"
    )

    print(
        f"[rag] Query: {query}"
    )

    try:

        # ----------------------------------------------------
        # Check whether this chat actually has a vectorstore.
        # ----------------------------------------------------

        if not vectorstore_exists(thread_id):

            print(
                f"[rag] No vectorstore found "
                f"for thread {thread_id}"
            )

            return {
                "context": ""
            }

        # ----------------------------------------------------
        # Load the existing FAISS vectorstore.
        # ----------------------------------------------------

        vectorstore = load_vectorstore(
            thread_id
        )

        print(
            "[rag] Vectorstore loaded successfully"
        )

        # ----------------------------------------------------
        # Create QUERY embedding.
        #
        # Do not use RETRIEVAL_DOCUMENT for the query.
        # ----------------------------------------------------

        query_embedding_model = (
            get_query_embedding_model()
        )

        query_vector = (
            query_embedding_model.embed_query(
                query
            )
        )

        print(
            "[rag] Query embedding generated"
        )

        # ----------------------------------------------------
        # Search FAISS directly using the query vector.
        # ----------------------------------------------------

        documents = (
            vectorstore.similarity_search_by_vector(
                query_vector,
                k=5,
            )
        )

        print(
            f"[rag] Retrieved "
            f"{len(documents)} document chunks"
        )

        if not documents:

            print(
                "[rag] No relevant document chunks found"
            )

            return {
                "context": ""
            }

        # ----------------------------------------------------
        # Format retrieved documents.
        # ----------------------------------------------------

        context_parts = []

        for index, document in enumerate(
            documents,
            start=1,
        ):

            page = document.metadata.get(
                "page"
            )

            source = document.metadata.get(
                "source"
            )

            metadata_text = ""

            if page is not None:
                metadata_text += (
                    f"Page: {page + 1}\n"
                )

            if source:
                metadata_text += (
                    f"Source: {source}\n"
                )

            context_parts.append(
                (
                    f"--- Document Chunk {index} ---\n"
                    f"{metadata_text}"
                    f"{document.page_content}\n"
                )
            )

        context = "\n".join(
            context_parts
        )

        print(
            "[rag] Context created successfully"
        )

        print(
            f"[rag] Context length: "
            f"{len(context)} characters"
        )

        return {
            "context": context
        }

    except Exception as error:

        print(
            "[rag] RETRIEVAL ERROR"
        )

        print(
            f"[rag] {type(error).__name__}: "
            f"{error}"
        )

        traceback.print_exc()

        # Do not crash the complete chatbot.
        # Return empty context, but LOG the actual error.
        return {
            "context": ""
        }


# ============================================================
# 10. AGENT NODE
# ============================================================

def agent_node(
    state: ChatState,
) -> ChatState:

    if state.get("blocked"):

        reason = state.get(
            "block_reason",
            "This request was blocked by guardrails.",
        )

        return {
            "messages": [
                AIMessage(
                    content=(
                        f"I can't help with that: "
                        f"{reason}"
                    )
                )
            ]
        }

    context = state.get(
        "context",
        ""
    )

    # --------------------------------------------------------
    # Strong PDF/RAG instructions.
    # --------------------------------------------------------

    rag_instruction = """
You have access to a retrieved document context below.

IMPORTANT RULES FOR DOCUMENT QUESTIONS:

1. If the Retrieved Document Context contains information,
   use it to answer the user's question.

2. Do NOT say that the PDF is missing if retrieved context
   is present.

3. Do NOT invent information that is not supported by the
   retrieved document when the user asks about the PDF.

4. If the retrieved context is insufficient to answer the
   question, clearly say that the available document
   context does not contain enough information.

5. When useful, mention the relevant page number from the
   document metadata.

6. For "explain this PDF" requests, provide a clear summary,
   important concepts, and key points from the retrieved
   content.

7. You can still answer normal questions using your general
   knowledge when the user is not asking about the uploaded
   document.
"""

    if context:

        document_context = context

    else:

        document_context = (
            "No relevant document context was retrieved."
        )

    system = SystemMessage(
        content=(
            f"{SYSTEM_PROMPT}\n\n"

            "You also have tools available to send emails "
            "and manage Google Calendar events.\n\n"

            "Use a tool only when the user's request clearly "
            "asks for that action.\n\n"

            "Do not call Gmail or Calendar tools unnecessarily.\n\n"

            f"{rag_instruction}\n"

            "==============================\n"
            "RETRIEVED DOCUMENT CONTEXT\n"
            "==============================\n\n"

            f"{document_context}\n\n"

            "==============================\n"
            "END DOCUMENT CONTEXT\n"
            "=============================="
        )
    )

    response = llm_with_tools.invoke(
        [
            system
        ]
        +
        state["messages"]
    )

    return {
        "messages": [
            response
        ]
    }


# ============================================================
# 11. OUTPUT GUARDRAIL
# ============================================================

def guardrail_output_node(
    state: ChatState,
) -> ChatState:

    last_message = state[
        "messages"
    ][-1]

    # Tool messages / non-string messages
    # should pass through unchanged.

    if (
        not isinstance(
            last_message,
            AIMessage
        )
        or not isinstance(
            last_message.content,
            str
        )
    ):

        return {}

    result = check_output(
        last_message.content
    )

    last_message.content = (
        result.sanitized_text
        if result.allowed
        else result.reason
    )

    return {}


# ============================================================
# 12. CHAT TITLE GENERATION
# ============================================================

def generate_chat_title(
    first_message: str,
) -> str:

    prompt = f"""
You are an AI that creates very short conversation titles.

Rules:
- Maximum 2 or 3 words.
- No punctuation.
- No quotation marks.
- No emojis.
- Return ONLY the title.

User Message:
{first_message}
"""

    try:

        response = llm.invoke(
            prompt
        )

        title = (
            response.content
            .strip()
            .replace(
                '"',
                ""
            )
            .replace(
                "'",
                ""
            )
        )

        title = " ".join(
            title.split()[:3]
        )

        return (
            title
            or "New Chat"
        )

    except Exception as error:

        print(
            f"[title] Error: {error}"
        )

        return "New Chat"


# ============================================================
# 13. LANGGRAPH GRAPH
# ============================================================

def create_graph(
    checkpointer,
):

    graph = StateGraph(
        ChatState
    )

    # --------------------------------------------------------
    # Nodes
    # --------------------------------------------------------

    graph.add_node(
        "guardrail_input",
        guardrail_input_node,
    )

    graph.add_node(
        "retrieve_node",
        retrieve_node,
    )

    graph.add_node(
        "agent_node",
        agent_node,
    )

    graph.add_node(
        "guardrail_output",
        guardrail_output_node,
    )

    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    graph.add_edge(
        START,
        "guardrail_input",
    )

    # --------------------------------------------------------
    # Guardrail -> RAG
    # --------------------------------------------------------

    graph.add_edge(
        "guardrail_input",
        "retrieve_node",
    )

    # --------------------------------------------------------
    # RAG -> Agent
    # --------------------------------------------------------

    graph.add_edge(
        "retrieve_node",
        "agent_node",
    )

    # --------------------------------------------------------
    # MCP TOOLS
    # --------------------------------------------------------

    if MCP_TOOLS:

        print(
            "[graph] MCP tools enabled"
        )

        graph.add_node(
            "tools",
            ToolNode(
                MCP_TOOLS
            ),
        )

        graph.add_conditional_edges(
            "agent_node",
            tools_condition,
            {
                "tools": "tools",
                END: "guardrail_output",
            },
        )

        # Tool result -> Agent
        graph.add_edge(
            "tools",
            "agent_node",
        )

    else:

        print(
            "[graph] Running without MCP tools"
        )

        graph.add_edge(
            "agent_node",
            "guardrail_output",
        )

    # --------------------------------------------------------
    # Output guardrail -> END
    # --------------------------------------------------------

    graph.add_edge(
        "guardrail_output",
        END,
    )

    # --------------------------------------------------------
    # Compile graph
    # --------------------------------------------------------

    return graph.compile(
        checkpointer=checkpointer
    )


# ============================================================
# 14. ASYNC CHATBOT RUNNER
# ============================================================

async def run_chatbot(
    input_data,
    config,
):

    # --------------------------------------------------------
    # Initialize MCP inside running event loop.
    # --------------------------------------------------------

    await initialize_mcp_tools()

    # --------------------------------------------------------
    # SQLite checkpointing.
    # --------------------------------------------------------

    async with AsyncSqliteSaver.from_conn_string(
        "chatbot.db"
    ) as checkpointer:

        # ----------------------------------------------------
        # Create LangGraph after MCP initialization.
        # ----------------------------------------------------

        chatbot = create_graph(
            checkpointer
        )

        # ----------------------------------------------------
        # Execute graph asynchronously.
        # ----------------------------------------------------

        result = await chatbot.ainvoke(
            input_data,
            config=config,
        )

        return result