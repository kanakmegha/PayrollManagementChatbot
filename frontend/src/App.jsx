import { useState, useEffect, useRef } from "react";
import axios from "axios";

function App() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([
    { role: 'ai', text: 'Hello! Ask me anything about payroll.' }
  ]);
  const [loading, setLoading] = useState(false);
  const [countdown, setCountdown] = useState(0); // Track waking up time
  const scrollRef = useRef(null);
  
  const BACKEND_URL = "https://payrollmanagementchatbot.onrender.com";

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Countdown Logic: Runs whenever countdown > 0
  useEffect(() => {
    if (countdown <= 0) return;

    const timer = setInterval(() => {
      setCountdown((prev) => prev - 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [countdown]);

  const sendQuery = async () => {
    if (!query.trim() || loading) return;
  
    const userMsg = { role: 'user', text: query };
    setMessages((prev) => [...prev, userMsg]);
    const currentQuery = query;
    setQuery("");
    setLoading(true);
  
    // Add an empty AI message that we will "fill" as the stream arrives
    setMessages((prev) => [...prev, { role: 'ai', text: "" }]);
  
    try {
      const response = await fetch(`${BACKEND_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: currentQuery }),
      });
  
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
  
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
  
        const chunk = decoder.decode(value, { stream: true });
        
        // Chunks come in as: {"answer": "Hello"}\n{"answer": " world"}
        const lines = chunk.split("\n").filter(line => line.trim());
        
        for (const line of lines) {
          const parsed = JSON.parse(line);
          setMessages((prev) => {
            const newMessages = [...prev];
            const lastMsg = newMessages[newMessages.length - 1];
            lastMsg.text += parsed.answer; // Append the new word
            return newMessages;
          });
        }
      }
    } catch (err) {
      console.error("Streaming error:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ height: '100vh', width: '100vw', display: 'flex', justifyContent: 'center', alignItems: 'center', background: '#f3f4f6' }}>
      <div style={{ width: '95%', maxWidth: '500px', height: '85vh', backgroundColor: '#fff', borderRadius: '15px', display: 'flex', flexDirection: 'column', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
        
        <div style={{ padding: '15px', borderBottom: '1px solid #eee', fontWeight: 'bold', color: '#4F46E5', display: 'flex', justifyContent: 'space-between' }}>
          <span>Payroll AI Support</span>
          {countdown > 0 && <span style={{ color: '#ef4444', fontSize: '12px' }}>Waking AI: {countdown}s</span>}
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '15px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {messages.map((msg, i) => (
            <div key={i} style={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              backgroundColor: msg.role === 'user' ? '#4F46E5' : '#f1f1f1',
              color: msg.role === 'user' ? '#fff' : '#333',
              padding: '8px 12px', borderRadius: '12px', maxWidth: '80%', fontSize: '14px'
            }}>
              {msg.text}
            </div>
          ))}
          
          {/* Enhanced Loading States */}
          {loading && countdown === 0 && <div style={{ fontSize: '12px', color: '#999' }}>AI is thinking...</div>}
          {countdown > 0 && (
            <div style={{ fontSize: '12px', color: '#ef4444', fontStyle: 'italic' }}>
              🧠 Model is loading. Please wait... auto-retrying in {countdown}s.
            </div>
          )}
          
          <div ref={scrollRef} />
        </div>

        <div style={{ padding: '15px', borderTop: '1px solid #eee', display: 'flex', gap: '10px' }}>
          <input 
            value={query} 
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendQuery()}
            placeholder={countdown > 0 ? "Waiting for AI..." : "Ask a question..."}
            disabled={loading || countdown > 0}
            style={{ flex: 1, padding: '10px', borderRadius: '8px', border: '1px solid #ddd', backgroundColor: countdown > 0 ? '#f9fafb' : '#fff' }}
          />
          <button 
            onClick={() => sendQuery()} 
            disabled={loading || countdown > 0}
            style={{ padding: '10px 20px', background: (loading || countdown > 0) ? '#9ca3af' : '#4F46E5', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer' }}
          >
            {countdown > 0 ? "Wait" : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;