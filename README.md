🤖 Nova — AI Voice Assistant & Productivity Copilot



A full-stack AI-powered productivity assistant built with React, Vite, FastAPI, LangGraph, Groq, Gemini Embeddings, FAISS, SQLite, and MCP.

Nova is an intelligent conversational assistant that goes beyond normal AI chat. It can maintain persistent conversations, understand uploaded PDF documents, process voice input, retrieve relevant document information using RAG, and interact with external productivity services such as Gmail and Google Calendar through the Model Context Protocol (MCP).

The project started with a Streamlit-based interface and has been migrated to a modern React + Vite frontend while keeping the core AI, RAG, MCP, and persistence architecture.





🚀 Project Overview

Nova combines conversational AI, agentic workflows, document intelligence, voice interaction, and external tool execution into a single application.

The assistant can:





💬 Have multi-turn AI conversations



🧵 Create and maintain multiple chat threads



📝 Automatically generate conversation titles



✏️ Rename conversations



🗑️ Delete conversations



📄 Upload and understand PDF documents



🧠 Retrieve relevant PDF information using RAG



🎙️ Convert voice input into text



📧 Read and send Gmail messages



📅 Read and create Google Calendar events



🔌 Execute external actions through MCP



🛡️ Apply input/output guardrails



💾 Persist conversations using SQLite



⚡ Run asynchronous MCP and LangGraph workflows





✨ Key Features



💬 1. Conversational AI

Nova provides natural multi-turn conversations powered by a Groq-hosted LLM.

Features





Natural language conversations



Multi-turn context



Persistent chat threads



Create new conversations



Rename conversations



Delete conversations



Resume previous conversations



Automatic conversation titles



LangGraph-based agent workflow

Example:

User:
Explain the difference between BFS and DFS.





📧 2. Gmail Integration

Nova can interact with Gmail using MCP.

Current Gmail capabilities





List recent emails



Search/retrieve email information



Send emails



Process natural-language email requests



Example

Show my 3 most recent emails.

Send an email to example@gmail.com saying the project demo is ready.





📅 3. Google Calendar Integration

Nova can interact with Google Calendar using MCP.

Current Calendar capabilities





List upcoming events



Create calendar events



Handle natural-language scheduling requests



Work with event dates and times



Example

Show my upcoming calendar events.

Create a meeting tomorrow at 5 PM for 30 minutes called Project Demo.





🔌 4. Model Context Protocol (MCP)

Nova uses the Model Context Protocol (MCP) to connect the AI agent with external productivity services.

Current MCP Tools

send_email
list_recent_emails
create_event
list_upcoming_events



MCP Architecture

                    ┌──────────────────────┐
                    │         Nova         │
                    │    AI Assistant      │
                    └──────────┬───────────┘
                               │
                         LangGraph Agent
                               │
                           MCP Client
                               │
                  ┌────────────┴────────────┐
                  │                         │
                  ▼                         ▼
             Gmail MCP               Calendar MCP
                  │                         │
                  ▼                         ▼
              Gmail API             Google Calendar





🧠 5. LangGraph Agent

Nova uses LangGraph to orchestrate the complete AI workflow.

The agent is responsible for:





Processing user input



Applying input guardrails



Retrieving relevant documents



Calling the LLM



Detecting when tools are required



Executing MCP tools



Processing tool results



Applying output guardrails



Returning the final response



LangGraph Workflow

START
  │
  ▼
guardrail_input
  │
  ▼
retrieve_node
  │
  ▼
agent_node
  │
  ├───────────────┐
  │               │
  │          Tool requested
  │               │
  │               ▼
  │            ToolNode
  │               │
  │               ▼
  │           agent_node
  │
  ▼
guardrail_output
  │
  ▼
END

The workflow uses asynchronous execution because MCP tools and SQLite checkpointing are async-compatible components.





📄 6. PDF RAG — Retrieval-Augmented Generation

Nova can understand user-uploaded PDF documents using a RAG pipeline.

The system:





Loads the PDF



Extracts document content



Splits the content into chunks



Generates Gemini embeddings



Stores vectors in FAISS



Performs similarity search



Retrieves relevant document chunks



Provides the retrieved context to the AI agent



Generates a grounded response



RAG Pipeline

PDF Upload
    │
    ▼
PyPDFLoader
    │
    ▼
Document Text
    │
    ▼
RecursiveCharacterTextSplitter
    │
    ▼
Document Chunks
    │
    ▼
Gemini Embeddings
    │
    ▼
FAISS Vector Store
    │
    ▼
Similarity Search
    │
    ▼
Relevant Context
    │
    ▼
LangGraph Agent
    │
    ▼
Groq LLM
    │
    ▼
Grounded Answer





🧠 RAG Improvements

The current RAG implementation uses separate embedding configurations for documents and queries.

Document embeddings

models/gemini-embedding-001
task_type = retrieval_document



Query embeddings

models/gemini-embedding-001
task_type = retrieval_query

The query is embedded and searched directly against the FAISS vector store using similarity search.

The system retrieves multiple relevant chunks instead of depending on the model to answer without document context.





🎙️ 7. Voice Input

Nova supports voice interaction using Groq Whisper for speech-to-text.

Voice Pipeline

Microphone
    │
    ▼
Audio Recording
    │
    ▼
React Frontend
    │
    ▼
FastAPI
    │
    ▼
Groq Whisper
    │
    ▼
Transcribed Text
    │
    ▼
Normal Nova Chat Workflow

Voice input is converted into normal text before being passed into the main chatbot workflow.





🛡️ 8. Guardrails

Nova includes a guardrail layer to improve safety and control the AI workflow.

The guardrail system handles areas such as:





Input validation



Prompt-injection protection



Unsafe-content filtering



PII protection



Output filtering



Protection against exposing internal instructions



Controlled external tool usage

User Input
    │
    ▼
Input Guardrail
    │
    ▼
AI / RAG / MCP
    │
    ▼
Output Guardrail
    │
    ▼
User Response





💾 9. Persistent Conversations

Nova uses SQLite for persistent conversation state.

LangGraph uses:

AsyncSqliteSaver

for asynchronous checkpointing.

LangGraph
    │
    ▼
AsyncSqliteSaver
    │
    ▼
SQLite Database

Thread metadata such as:





Thread ID



Chat title



Rename state



Deleted threads

is managed through database.py.





⚡ 10. Async MCP Architecture

An important project improvement was fixing MCP initialization for FastAPI's asynchronous environment.

The earlier approach used:

asyncio.run(get_mcp_tools())

inside an environment where an event loop was already running. This produced:

asyncio.run() cannot be called from a running event loop

The current implementation initializes MCP tools asynchronously during chatbot execution.

Expected tools:

[mcp] Loading MCP tools...
[mcp] Loaded 4 MCP tools

[mcp] Tool available: send_email
[mcp] Tool available: list_recent_emails
[mcp] Tool available: create_event
[mcp] Tool available: list_upcoming_events

This allows Gmail and Calendar MCP functionality to work correctly with FastAPI/Uvicorn.





⚛️ 11. React + Vite Frontend

The original project used Streamlit. The current project uses a modern React + Vite frontend.

The React interface handles:





Chat interface



Conversation list



New chat



Chat switching



Chat renaming



Chat deletion



PDF upload



Voice recording



Message rendering



Loading states



Error handling



Backend API communication



Frontend Architecture

React UI
   │
   ▼
api.js
   │
   ▼
FastAPI REST API
   │
   ▼
Nova Backend

The API base URL is configured using:

const API =
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000/api";





🐍 12. FastAPI Backend

The FastAPI backend provides the REST API used by the React frontend.

Main backend file:

backend/api.py

Responsibilities:





Chat requests



Chat thread management



PDF uploads



Audio transcription



CORS



RAG integration



AI workflow execution





🔗 API Endpoints







Method



Endpoint



Purpose





GET



/api/health



Backend health check





GET



/api/chats



Get chat threads





POST



/api/chats



Create a new chat





GET



/api/chats/{thread_id}



Get chat messages





PATCH



/api/chats/{thread_id}



Rename chat





DELETE



/api/chats/{thread_id}



Delete chat





POST



/api/chat



Send a message





POST



/api/chats/{thread_id}/pdf



Upload PDF





POST



/api/transcribe



Transcribe audio





🏗️ Complete System Architecture

                         ┌───────────────────────────┐
                         │       React + Vite        │
                         │        Frontend           │
                         └─────────────┬─────────────┘
                                       │
                                  REST API
                                       │
                         ┌─────────────▼─────────────┐
                         │        FastAPI             │
                         │         Backend            │
                         └─────────────┬─────────────┘
                                       │
                              ┌────────▼────────┐
                              │   LangGraph     │
                              │     Agent       │
                              └────────┬────────┘
                                       │
                 ┌─────────────────────┼─────────────────────┐
                 │                     │                     │
                 ▼                     ▼                     ▼
             Guardrails              RAG                MCP Tools
                 │                     │                     │
                 │                     ▼              ┌──────┴──────┐
                 │                   FAISS            │             │
                 │                     │              ▼             ▼
                 │             Gemini Embeddings   Gmail       Calendar
                 │                     │              │             │
                 │                     │              ▼             ▼
                 │                     │          Gmail API    Calendar API
                 │                     │
                 └─────────────────────┼─────────────────────┐
                                       │                     │
                                       ▼                     ▼
                                  Groq LLM              SQLite





🛠️ Technology Stack







Layer



Technology





Frontend



React + Vite





Frontend Language



JavaScript





Backend



FastAPI





Backend Language



Python





AI Agent



LangGraph





LLM Framework



LangChain





LLM



Groq





Speech-to-Text



Groq Whisper





Embeddings



Google Gemini





Embedding Model



models/gemini-embedding-001





Vector Store



FAISS





RAG



LangChain + FAISS





Database



SQLite





Checkpointing



AsyncSqliteSaver





Tool Protocol



MCP





Email



Gmail





Calendar



Google Calendar





Authentication



Google OAuth





Environment



python-dotenv





Version Control



Git + GitHub





📁 Project Structure

nova-ai-assistant/
│
├── backend/
│   ├── __init__.py
│   └── api.py
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   ├── main.jsx
│   │   └── styles.css
│   │
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.js
│
├── rag/
│   ├── __init__.py
│   ├── embeddings.py
│   ├── loader.py
│   ├── prompts.py
│   └── retriever.py
│
├── backend_sqlite.py
├── frontend_sqlite.py
├── database.py
├── guardrails.py
├── mcp_client.py
├── email_server.py
├── calendar_server.py
│
├── requirements.txt
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
└── SETUP_PHASE1.md





📂 Important Files



backend/api.py

FastAPI REST API layer for chat, threads, PDF upload, transcription, and CORS.

backend_sqlite.py

Core AI backend containing LangGraph, Groq LLM, RAG retrieval, MCP tools, SQLite checkpointing, and voice transcription.

database.py

Chat/thread metadata management.

guardrails.py

Input and output safety logic.

mcp_client.py

MCP client initialization and tool loading.

email_server.py

Gmail MCP server.

calendar_server.py

Google Calendar MCP server.

rag/loader.py

PDF loading and document splitting.

rag/embeddings.py

Gemini embeddings and FAISS vector-store operations.

rag/retriever.py

Document retrieval logic.

frontend/src/App.jsx

Main React application interface.

frontend/src/api.js

Frontend-to-backend API communication.





🚀 Getting Started



1. Clone Repository

git clone https://github.com/nishantkushwaha76/nova-ai-assistant.git
cd nova-ai-assistant





🐍 Backend Setup



2. Create Virtual Environment

Windows:

python -m venv .venv

Activate:

.venv\Scripts\activate





3. Install Python Dependencies

pip install -r requirements.txt





🔐 Environment Variables

Create a .env file in the project root.

Example:

GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

Never upload the real .env file to GitHub.

Use .env.example as the safe configuration template.





🔑 Google OAuth Setup

Gmail and Google Calendar functionality requires Google OAuth.

General setup:

Google Cloud Console
        │
        ▼
Create / Select Project
        │
        ▼
Enable Gmail API
        │
        ▼
Enable Google Calendar API
        │
        ▼
Configure OAuth Consent Screen
        │
        ▼
Create OAuth Credentials
        │
        ▼
Configure MCP
        │
        ▼
Authenticate Google Account

Never upload:

credentials.json
gmail_token.json
OAuth tokens
API keys





⚛️ Frontend Setup

Open a second terminal:

cd frontend
npm install
npm run dev

Frontend:

http://localhost:5173





🚀 Start Backend

From the project root:

uvicorn backend.api:app --reload --port 8000

Backend:

http://localhost:8000

FastAPI documentation:

http://localhost:8000/docs





🔄 Run Both Services



Terminal 1 — Backend

cd nova-ai-assistant
.venv\Scripts\activate
uvicorn backend.api:app --reload --port 8000



Terminal 2 — Frontend

cd nova-ai-assistant\frontend
npm run dev

Then open:

http://localhost:5173





🧪 Testing



Basic Chat

Hello Nova.



Gmail

Show my 3 most recent emails.



Calendar

Show my upcoming calendar events.



Gmail + Calendar

Show my recent emails and upcoming calendar events.



Send Email

Send an email to example@gmail.com saying the project demo is ready.



Create Calendar Event

Create a meeting tomorrow at 5 PM for 30 minutes called Nova Demo.



PDF RAG

Upload a PDF and ask:

Summarize this document.

or:

Explain the algorithm used in this PDF.



Voice

Use the microphone and ask:

What is the difference between TCP and UDP?





🧪 MCP Integration Test

A complete MCP test can be performed with one request:

Show my 3 most recent emails, show my upcoming calendar events, send an email to example@gmail.com saying "Nova MCP integration test successful", and create a calendar event tomorrow at 5 PM for 30 minutes called "Nova MCP Demo".

This tests:

list_recent_emails
+
list_upcoming_events
+
send_email
+
create_event





🐛 Troubleshooting



Backend Does Not Start

.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.api:app --reload --port 8000



Frontend Does Not Start

cd frontend
npm install
npm run dev



CORS Error

Make sure the frontend is running on:

http://localhost:5173

and that this origin is allowed by FastAPI.

Gmail / Calendar Not Working

Check:





Google OAuth configuration



Gmail API enabled



Google Calendar API enabled



OAuth authentication completed



MCP configuration



Backend logs

Expected MCP tools:

send_email
list_recent_emails
create_event
list_upcoming_events



MCP Event Loop Error

If you see:

asyncio.run() cannot be called from a running event loop

make sure MCP tools are initialized asynchronously and not through a nested asyncio.run() inside FastAPI/Uvicorn.

PDF RAG Not Working

Check:

GEMINI_API_KEY=your_gemini_api_key_here

Also verify:





PDF upload succeeds



PDF contains readable text



Gemini API key is valid



FAISS vector store is created



Query embeddings are available



Backend logs contain no embedding errors





🔒 Security

Never commit:

.env
credentials.json
gmail_token.json
OAuth tokens
API keys
database files
FAISS vector stores
private credentials

The .gitignore file is configured to exclude sensitive and generated files.

If an API key is accidentally exposed:





Revoke the key immediately.



Generate a new key.



Update .env.



Remove the secret from Git history if required.



Push only the sanitized repository.





🌿 Git Workflow

Check changes:

git status

Stage:

git add .

Commit:

git commit -m "Describe your changes"

Push:

git push





📈 Current Project Status



Core AI





✅ Groq LLM



✅ LangGraph Agent



✅ LangChain



✅ Persistent conversations



✅ Automatic chat titles



Frontend





✅ React



✅ Vite



✅ Chat interface



✅ Chat threads



✅ Rename chats



✅ Delete chats



✅ PDF upload



✅ Voice interface



✅ API integration



RAG





✅ PDF loading



✅ Text splitting



✅ Gemini embeddings



✅ FAISS vector store



✅ Query embeddings



✅ Similarity search



✅ Thread-based vector stores



✅ Retrieved context passed to agent



Voice





✅ Audio recording



✅ FastAPI transcription endpoint



✅ Groq Whisper



✅ Voice-to-text workflow



MCP





✅ MCP client



✅ Async MCP initialization



✅ Gmail integration



✅ Google Calendar integration



✅ send_email



✅ list_recent_emails



✅ create_event



✅ list_upcoming_events



Persistence





✅ SQLite



✅ AsyncSqliteSaver



✅ Persistent LangGraph checkpoints



✅ Chat thread metadata



Security





✅ Input guardrails



✅ Output guardrails



✅ PII protection



✅ Prompt-injection protection



✅ .gitignore protection for secrets





🔮 Future Improvements





🔊 Text-to-speech responses



⚡ Token-by-token streaming



🧠 Advanced long-term memory



🔐 User authentication



👥 Multi-user support



☁️ Cloud deployment



📱 Mobile application



🔌 Additional MCP integrations



📚 Multiple document collections



🔎 Improved RAG reranking



📊 Advanced monitoring



🧪 Automated unit and integration testing



🔔 Notifications



🗓️ Advanced calendar workflows



📧 Advanced Gmail search and management



🎨 Further UI/UX improvements





🎯 Why Nova?

Nova combines several modern AI technologies into one practical system:

Generative AI
      +
Agentic AI
      +
RAG
      +
Vector Search
      +
Voice AI
      +
MCP
      +
Gmail
      +
Google Calendar
      +
FastAPI
      +
React
      +
SQLite

The result is a productivity assistant capable of both:

Understanding information

and

Taking real-world actions.





📚 Learning Areas Demonstrated

This project demonstrates practical implementation of:





Large Language Models



Generative AI



Agentic workflows



LangGraph



LangChain



Retrieval-Augmented Generation



Embeddings



Vector databases



FAISS similarity search



Speech-to-text



REST APIs



FastAPI



React



Vite



SQLite



Async programming



MCP



Gmail API



Google Calendar API



OAuth



Prompt engineering



Guardrails



Git and GitHub





📜 License

This project is licensed under the terms specified in the repository's LICENSE file.





👨‍💻 Author


KHUSHI KUMARI
AYUSH KUMAR
Nishant Kushwaha

GitHub:

https://github.com/nishantkushwaha76

Project Repository:

https://github.com/nishantkushwaha76/nova-ai-assistant





⭐ Nova



Understand. Retrieve. Reason. Act. Respond.

Nova combines:

📄 Document Understanding
🎙️ Voice Interaction
📧 Email Automation
📅 Calendar Management
🔌 External Tools
🧠 Agentic Reasoning
💾 Persistent Memory
🛡️ Guardrails

into one AI-powered productivity assistant.