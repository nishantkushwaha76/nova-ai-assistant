# React Frontend

This folder contains the React/Vite frontend for the AI Assistant.

## Run

From the `frontend` folder:

```bash
npm install
npm run dev
```

The frontend expects the FastAPI backend at:

```text
http://localhost:8000
```

You can override it with a `.env` file:

```env
VITE_API_URL=http://localhost:8000/api
```

## Backend

From the project root:

```bash
uvicorn backend.api:app --reload --port 8000
```

## Features kept from the Streamlit version

- Chat threads
- New chat
- Rename chat
- Delete chat
- Persistent conversation history
- PDF upload for RAG
- Voice input and transcription
- Normal LangGraph chatbot flow
- Gmail MCP actions through the backend
- Google Calendar MCP actions through the backend

The React app is intentionally kept simple: normal spacing, basic borders, limited colors, and no large gradients or decorative effects.
