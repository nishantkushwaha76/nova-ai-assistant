# MEMORY.md — AI Voice Assistant Project
_Last updated: 2026-09-26_

## Project
**Name:** AI Voice Assistant / Productivity Copilot  
**Path:** `E:\5TH SEM BVP\AI\PBL\AI-voice-assistant`

The project is a conversational AI assistant supporting text chat, persistent threads, PDF RAG, voice input/STT, LangGraph, MCP tools, Gmail, Google Calendar, and guardrails.

## Current Status
The chatbot is working successfully.

Verified:
- Streamlit chatbot
- LangGraph workflow
- Groq LLM
- PDF upload + RAG
- FAISS retrieval
- SQLite persistence
- Async SQLite checkpointing
- Chat threads, rename/delete
- Input/output guardrails
- Voice recording
- Groq Whisper Large V3 Turbo STT
- Gmail MCP
- Google Calendar MCP
- Multiple MCP tools in one request
- Voice → STT → normal chatbot workflow

Current immediate goal: safely prepare and push the project to GitHub.

## Core Architecture

```text
Streamlit UI
   ├── Text Input ──────────────┐
   └── Voice Input              │
          ↓                     │
      Audio bytes               │
          ↓                     │
   Groq Whisper STT             │
          ↓                     │
   Transcribed text ────────────┘
                ↓
             user_input
                ↓
        Input Guardrail
                ↓
          RAG Retrieval
                ↓
           Agent / LLM
                ↓
        ┌───────┴────────┐
        │                │
   Normal answer      MCP ToolNode
                         ↓
                 ┌───────┴────────┐
                 ↓                ↓
             Gmail MCP       Calendar MCP
                 ↓                ↓
             Gmail API      Google Calendar API
                 └───────┬────────┘
                         ↓
                  Output Guardrail
                         ↓
                      Response
```

## Critical Design Principle

Text and voice must converge into the same workflow:

```text
Text ───────────────┐
                    ├──> user_input ──> existing chatbot workflow
Voice -> STT ───────┘
```

Do not create a separate chatbot workflow for voice.

## Voice Input

The microphone belongs in the frontend; audio-to-text belongs in the backend.

Frontend uses:

```python
if "voice_input_key" not in st.session_state:
    st.session_state["voice_input_key"] = 0

voice_data = st.audio_input(
    "🎤 Record your voice",
    key=f"voice_input_{st.session_state['voice_input_key']}"
)
```

Processing:

```python
if voice_data is not None:
    with st.spinner("Converting speech to text..."):
        user_input = transcribe_audio(voice_data.getvalue())

    st.session_state["voice_input_key"] += 1
```

Changing the widget key is essential. It destroys the old audio widget and creates a fresh recorder after every processed recording. This fixed the earlier issue where the old recording remained with Play/Pause controls and also appeared in new chats.

Old `hashlib` / `last_voice_hash` logic is no longer needed.

## STT

Selected engine:

**Groq Whisper Large V3 Turbo**

It is hosted, avoids a local Whisper model, and fits the existing Groq stack.

`langchain-groq` is used for LangChain LLM integration; the direct `groq` Python SDK is used for STT.

## Verified Versions

```text
streamlit==1.64.0
langchain-groq==1.1.3
groq==0.37.1
```

Verify with:

```powershell
python -c "import streamlit, langchain_groq, groq; print('streamlit:', streamlit.__version__); print('langchain-groq:', langchain_groq.__version__); print('groq:', groq.__version__)"
```

Expected:

```text
streamlit: 1.64.0
langchain-groq: 1.1.3
groq: 0.37.1
```

Also:

```powershell
pip check
```

Expected:

```text
No broken requirements found.
```

`groq --version` is not a valid PowerShell command because Groq is a Python package.

A previous `pip install -U groq` upgraded Groq to `1.7.0`, which conflicted with `langchain-groq==1.1.3` (`groq<1.0.0,>=0.30.0`). This was fixed by installing `groq==0.37.1`.

Do not upgrade Groq blindly.

## requirements.txt

Intended current requirements:

```text
streamlit==1.64.0
python-dotenv

langchain
langchain-core
langchain-community
langchain-groq==1.1.3
langchain-google-genai

langgraph
langgraph-checkpoint-sqlite
aiosqlite

langchain-mcp-adapters
mcp

groq==0.37.1

faiss-cpu
pypdf

google-api-python-client
google-auth-httplib2
google-auth-oauthlib
```

Do not add `whisper`, `faster-whisper`, `openai-whisper`, or `torch` for the current hosted STT architecture.

## LangGraph Workflow

```text
START
  ↓
guardrail_input
  ↓
retrieve_node
  ↓
agent_node
  ├── tool requested → ToolNode → agent_node
  ↓
guardrail_output
  ↓
END
```

The graph uses `StateGraph(ChatState)` with:
- `guardrail_input`
- `retrieve_node`
- `agent_node`
- `guardrail_output`
- conditional `tools` node when `MCP_TOOLS` exists

Tool routing uses `tools_condition`.

## Async Architecture

MCP and SQLite checkpointing require async execution.

Runner:

```python
async def run_chatbot(input_data, config):
    conn, checkpointer = await create_checkpointer()

    try:
        chatbot = create_graph(checkpointer)

        result = await chatbot.ainvoke(
            input_data,
            config=config,
        )

        return result
    finally:
        await conn.close()
```

Use `await chatbot.ainvoke(...)`, not synchronous `.invoke()`.

Use `AsyncSqliteSaver`, not synchronous `SqliteSaver`.

## SQLite / Threads

Concept:

```text
LangGraph
   ↓
AsyncSqliteSaver
   ↓
chatbot.db
```

`database.py` manages thread metadata through:

```python
create_thread()
get_all_threads()
rename_thread()
delete_thread()
```

Conversation loading helper:

```python
def load_conversation(thread_id):
    state = chatbot.get_state(
        config={"configurable": {"thread_id": thread_id}}
    )
    return state.values.get("messages", [])
```

## RAG

Pipeline:

```text
PDF Upload
  ↓
Document Loader
  ↓
Text Splitting
  ↓
Embeddings
  ↓
FAISS Vector Store
  ↓
Similarity Retrieval
  ↓
Relevant Context
  ↓
LangGraph Agent
  ↓
Answer
```

Important `rag/` modules:
- `embeddings.py`
- `loader.py`
- `prompts.py`
- `retriever.py`

Frontend supports:

```python
chat_data = st.chat_input(
    "Type here...",
    accept_file=True,
    file_type=["pdf"],
)
```

## MCP

Architecture:

```text
LangGraph Agent
      ↓
ToolNode
      ↓
MCP Client
      ├── Gmail MCP → Gmail API
      └── Calendar MCP → Google Calendar API
```

The assistant can execute multiple MCP tools in one request.

### Gmail MCP
Working and tested:
- Read/search emails
- Send emails

An earlier guardrail issue converted an email address into `[REDACTED_EMAIL]`, making the MCP tool reject it. This was fixed in `guardrails.py`; email sending now works.

### Calendar MCP
Working and tested:
- Calendar interaction
- Upcoming event operations
- Event creation where supported

A combined Gmail + Calendar MCP test succeeded.

## Guardrails

`guardrails.py` handles:
- Prompt-injection protection
- Unsafe-content filtering
- Input validation
- Output filtering
- PII handling
- Internal-instruction protection

Do not bypass guardrails when modifying the workflow.

## File Responsibilities

```text
backend_sqlite.py
  - LangGraph graph
  - LLM
  - STT
  - RAG integration
  - MCP tools
  - checkpointing
  - async runner

frontend_sqlite.py
  - Streamlit UI
  - chat input
  - microphone
  - PDF upload
  - thread UI
  - new chat
  - rename/delete
  - message display

database.py
  - thread metadata
  - create/get/rename/delete

guardrails.py
  - input/output safety
  - PII handling

mcp_client.py
  - MCP client/tool loading

email_server.py
  - Gmail MCP server

calender_server.py
  - Google Calendar MCP server

rag/
  - PDF loading
  - chunking
  - embeddings
  - vector store
  - retrieval
```

Expected project structure:

```text
AI-voice-assistant/
├── backend_sqlite.py
├── frontend_sqlite.py
├── database.py
├── guardrails.py
├── mcp_client.py
├── email_server.py
├── calender_server.py
├── rag/
│   ├── __init__.py
│   ├── embeddings.py
│   ├── loader.py
│   ├── prompts.py
│   └── retriever.py
├── requirements.txt
├── README.md
├── .gitignore
└── .env
```

Check the actual repository before assuming every filename is present.

## README

A new README was generated covering:
- Project purpose
- Features
- Architecture
- LangGraph workflow
- RAG
- Voice/STT
- MCP
- Gmail
- Calendar
- Tech stack
- Project structure
- Installation
- Environment variables
- Example prompts
- Safety
- Async architecture
- Current status
- Future improvements

Project description used:

**AI Voice Assistant & Productivity Copilot**

## GitHub Preparation

Before pushing, verify `.gitignore`.

Never commit:

```text
.env
.venv/
chatbot.db
credentials.json
gmail_token.json
OAuth credentials
API keys
access tokens
generated audio
Python cache files
```

First:

```powershell
git status
```

Do not blindly run `git add .` until `.gitignore` is verified.

Candidate commit:

```powershell
git add .
git commit -m "feat: add voice input and MCP integrations"
git push origin main
```

## MIT License

A previous README contained:

```text
Copyright (c) 2026 Khushi Kumari
```

That should not remain if this is Ayush's project.

If using MIT:

```text
MIT License

Copyright (c) 2026 Ayush Kumar
```

MIT permits reuse, modification, distribution, sublicensing, and commercial use provided the copyright/license notice is retained. It also provides the software without warranty. MIT is optional.

## Testing History

STT file test succeeded with:

```text
hello this is the test of my AI voice assistant
```

Streamlit microphone test succeeded and saved an audio recording.

Integrated voice-to-text test succeeded with:

```text
There are five people in my room.
```

Voice was then integrated into the normal chatbot workflow successfully.

Gmail and Calendar MCP workflows were successfully tested, including a combined multi-tool request.

## Development Rules

The project already works. Do NOT rebuild it from scratch.

When changing it:
1. Preserve the existing text workflow.
2. Convert new input methods into `user_input`.
3. Keep STT in the backend.
4. Keep microphone UI in the frontend.
5. Keep MCP execution inside LangGraph.
6. Preserve async execution.
7. Keep RAG intact.
8. Pin critical dependencies when compatibility is verified.
9. Never commit secrets.
10. Test incrementally.
11. Inspect the current relevant file before changing exact code.
12. Make the smallest necessary modification.

## Useful Commands

Run:

```powershell
streamlit run frontend_sqlite.py
```

Check versions:

```powershell
python -c "import streamlit, langchain_groq, groq; print('streamlit:', streamlit.__version__); print('langchain-groq:', langchain_groq.__version__); print('groq:', groq.__version__)"
```

Check dependencies:

```powershell
pip check
```

Git:

```powershell
git status
```

## Immediate Next Workflow

```text
Finalize requirements.txt
        ↓
Finalize README.md
        ↓
Check MIT license ownership if used
        ↓
Verify .gitignore
        ↓
git status
        ↓
Ensure no secrets/databases/.venv are staged
        ↓
git add .
        ↓
git commit
        ↓
git push origin main
```

After this, continue development from the stable working chatbot.

# END OF MEMORY
