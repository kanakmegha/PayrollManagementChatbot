"use client";

import { useState } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    const res = await fetch("/api/chat", {
      method: "POST",
      body: JSON.stringify({ question: input }),
      headers: { "Content-Type": "application/json" },
    });

    const data = await res.json();

    const botMessage: Message = {
      role: "assistant",
      content: data.answer || "No response",
    };

    setMessages((prev) => [...prev, botMessage]);
    setInput("");
    setLoading(false);
  };

  return (
    <main className="w-full max-w-2xl mx-auto p-4">
      <h1 className="text-3xl font-bold mb-4 text-center">RAG Chatbot</h1>

      <div className="h-[70vh] overflow-y-auto border rounded-lg p-3 bg-white shadow">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`my-2 p-3 rounded-lg ${
              msg.role === "user"
                ? "bg-blue-100 text-right"
                : "bg-gray-100 text-left"
            }`}
          >
            {msg.content}
          </div>
        ))}

        {loading && (
          <div className="p-2 text-gray-400 italic">Thinking...</div>
        )}
      </div>

      <div className="mt-4 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask something..."
          className="flex-1 border px-3 py-2 rounded-lg"
        />
        <button
          onClick={sendMessage}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg"
        >
          Send
        </button>
      </div>
    </main>
  );
}
