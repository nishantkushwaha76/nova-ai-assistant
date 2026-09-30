const API = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }

  return data;
}

export const api = {
  chats: () => request("/chats"),

  newChat: () =>
    request("/chats", {
      method: "POST",
    }),

  messages: (id) => request(`/chats/${id}`),

  rename: (id, title) =>
    request(`/chats/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    }),

  remove: (id) =>
    request(`/chats/${id}`, {
      method: "DELETE",
    }),

  send: (thread_id, message) =>
    request("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thread_id, message }),
    }),

  uploadPdf: (id, file) => {
    const form = new FormData();
    form.append("file", file);

    return request(`/chats/${id}/pdf`, {
      method: "POST",
      body: form,
    });
  },

  transcribe: (blob) => {
    const form = new FormData();
    form.append("file", blob, "recording.webm");

    return request("/transcribe", {
      method: "POST",
      body: form,
    });
  },
};
