import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import {
  Bot,
  FileText,
  Menu,
  Mic,
  Paperclip,
  Plus,
  Send,
  Square,
  Trash2,
  X,
} from "lucide-react";

const QUICK_PROMPTS = [
  "What can you help me with?",
  "Check my upcoming calendar events",
  "List my recent emails",
  "Summarize my uploaded PDF",
];

function App() {
  const [chats, setChats] = useState([]);
  const [threadId, setThreadId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [error, setError] = useState("");

  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    loadChats();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function loadChats() {
    try {
      const data = await api.chats();
      setChats(data.chats || []);

      if (data.chats?.length) {
        await selectChat(data.chats[0].id);
      } else {
        await createChat();
      }
    } catch (err) {
      setError(err.message);
    }
  }

  async function createChat() {
    try {
      const chat = await api.newChat();
      setChats((prev) => [chat, ...prev]);
      setThreadId(chat.id);
      setMessages([]);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }

  async function selectChat(id) {
    try {
      const data = await api.messages(id);
      setThreadId(id);
      setMessages(data.messages || []);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }

  async function sendMessage(prompt = input) {
    const message = prompt.trim();

    if (!message || busy || !threadId) return;

    setInput("");
    setError("");
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setBusy(true);

    try {
      if (file) {
        await api.uploadPdf(threadId, file);
        setFile(null);
      }

      const data = await api.send(threadId, message);

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.response },
      ]);

      const refreshed = await api.chats();
      setChats(refreshed.chats || []);
    } catch (err) {
      setError(err.message);
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setBusy(false);
    }
  }

  async function deleteChat(id) {
    if (!window.confirm("Delete this conversation?")) return;

    try {
      await api.remove(id);

      const remaining = chats.filter((chat) => chat.id !== id);
      setChats(remaining);

      if (id === threadId) {
        if (remaining.length) {
          await selectChat(remaining[0].id);
        } else {
          await createChat();
        }
      }
    } catch (err) {
      setError(err.message);
    }
  }

  async function renameChat(chat) {
    const title = window.prompt("Rename conversation", chat.title);

    if (!title?.trim()) return;

    try {
      await api.rename(chat.id, title.trim());
      setChats((prev) =>
        prev.map((item) =>
          item.id === chat.id ? { ...item, title: title.trim() } : item
        )
      );
    } catch (err) {
      setError(err.message);
    }
  }

  async function toggleRecording() {
    if (recording) {
      recorderRef.current?.stop();
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Voice recording is not supported in this browser.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);

      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size) chunksRef.current.push(event.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        setRecording(false);
        setBusy(true);

        try {
          const blob = new Blob(chunksRef.current, { type: "audio/webm" });
          const data = await api.transcribe(blob);
          setInput(data.text || "");
        } catch (err) {
          setError(err.message);
        } finally {
          setBusy(false);
        }
      };

      recorderRef.current = recorder;
      recorder.start();
      setRecording(true);
      setError("");
    } catch {
      setError("Microphone permission is required.");
    }
  }

  const currentChat = chats.find((chat) => chat.id === threadId);

  return (
    <div className="app">
      <aside className={`sidebar ${sidebarOpen ? "open" : "closed"}`}>
        <div className="sidebar-head">
          <div className="brand">
            <div className="brand-icon">
              <Bot size={18} />
            </div>
            {sidebarOpen && (
              <div>
                <strong>Nova</strong>
                <span>AI Assistant</span>
              </div>
            )}
          </div>
        </div>

        {sidebarOpen && (
          <>
            <button className="new-chat" onClick={createChat}>
              <Plus size={17} />
              New chat
            </button>

            <div className="sidebar-title">Chats</div>

            <div className="chat-list">
              {chats.map((chat) => (
                <div
                  className={`chat-item ${
                    chat.id === threadId ? "selected" : ""
                  }`}
                  key={chat.id}
                >
                  <button
                    className="chat-name"
                    onClick={() => selectChat(chat.id)}
                    title={chat.title}
                  >
                    {chat.title}
                  </button>

                  <button
                    className="chat-more"
                    onClick={() => renameChat(chat)}
                    title="Rename"
                  >
                    ···
                  </button>
                </div>
              ))}
            </div>

            <div className="sidebar-footer">
              {threadId && (
                <button
                  className="delete-button"
                  onClick={() => deleteChat(threadId)}
                >
                  <Trash2 size={16} />
                  Delete current chat
                </button>
              )}
            </div>
          </>
        )}
      </aside>

      <main className="main">
        <header className="header">
          <button
            className="header-button"
            onClick={() => setSidebarOpen((value) => !value)}
            title="Toggle sidebar"
          >
            <Menu size={20} />
          </button>

          <div className="header-title">
            {currentChat?.title || "New chat"}
          </div>

          <div className="online">
            <span />
            Online
          </div>
        </header>

        <section className="chat-area">
          {messages.length === 0 ? (
            <div className="welcome">
              <div className="welcome-icon">
                <Bot size={30} />
              </div>
              <h1>How can I help?</h1>
              <p>
                Ask a question, upload a PDF, or use the assistant with your
                email and calendar.
              </p>

              <div className="quick-prompts">
                {QUICK_PROMPTS.map((prompt) => (
                  <button key={prompt} onClick={() => sendMessage(prompt)}>
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages">
              {messages.map((message, index) => (
                <div className={`message ${message.role}`} key={index}>
                  <div className="message-avatar">
                    {message.role === "assistant" ? (
                      <Bot size={16} />
                    ) : (
                      "You"
                    )}
                  </div>

                  <div className="message-body">
                    <div className="message-name">
                      {message.role === "assistant" ? "Nova" : "You"}
                    </div>
                    <div className="message-text">{message.content}</div>
                  </div>
                </div>
              ))}

              {busy && (
                <div className="message assistant">
                  <div className="message-avatar">
                    <Bot size={16} />
                  </div>
                  <div className="message-body">
                    <div className="message-name">Nova</div>
                    <div className="typing">Thinking...</div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </section>

        <div className="composer-area">
          {error && (
            <div className="error">
              <span>{error}</span>
              <button onClick={() => setError("")}>
                <X size={15} />
              </button>
            </div>
          )}

          {file && (
            <div className="attachment">
              <FileText size={16} />
              <span>{file.name}</span>
              <button onClick={() => setFile(null)}>
                <X size={15} />
              </button>
            </div>
          )}

          <div className="composer">
            <label className="attach-button" title="Attach PDF">
              <Paperclip size={19} />
              <input
                type="file"
                accept=".pdf,application/pdf"
                onChange={(event) =>
                  setFile(event.target.files?.[0] || null)
                }
              />
            </label>

            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  sendMessage();
                }
              }}
              placeholder="Type a message..."
              rows={1}
              disabled={busy}
            />

            <button
              className={`round-button ${recording ? "recording" : ""}`}
              onClick={toggleRecording}
              title={recording ? "Stop recording" : "Voice input"}
              disabled={busy && !recording}
            >
              {recording ? <Square size={17} /> : <Mic size={19} />}
            </button>

            <button
              className="send-button"
              onClick={() => sendMessage()}
              disabled={!input.trim() || busy}
              title="Send"
            >
              <Send size={18} />
            </button>
          </div>

          <div className="composer-note">
            Enter to send · Shift + Enter for a new line
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
