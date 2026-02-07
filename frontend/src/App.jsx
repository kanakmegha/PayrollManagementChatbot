import { useState, useEffect, useRef } from "react";
import axios from "axios";

// Accessing the URL from Vite environment variables
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;

function App() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([
    { role: 'ai', text: 'Hello! Ask me anything about payroll.' }
  ]);
  const [loading, setLoading] = useState(false);
  const [countdown, setCountdown] = useState(0); 
  const scrollRef = useRef(null);

  // Auto-scroll logic
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Countdown timer for 503 (Model Loading) errors
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

    try {
      // SYNCED WITH BACKEND: Using the /chat endpoint
      // No need to send 'documents' or 'Auth' here; 
      // the backend handles Supabase and Hugging Face tokens internally.
      const response = await axios.post(`${BACKEND_URL}/chat`, {
        question: currentQuery 
      });

      // Your backend returns: {"answer": "..."}
      const aiResponse = response.data.answer;

      setMessages((prev) => [...prev, { role: 'ai', text: aiResponse }]);

    } catch (err) {
      console.error("Connection error:", err);
      
      // Handle Model Loading (Common on Hugging Face Free Tier)
      if (err.response?.status === 503) {
        setCountdown(20);
        setMessages((prev) => [...prev, { 
          role: 'ai', 
          text: "The payroll engine is warming up (503). Retrying in 20 seconds..." 
        }]);
      } else {
        setMessages((prev) => [...prev, { 
          role: 'ai', 
          text: "I'm having trouble connecting to the payroll engine. Please check the backend logs." 
        }]);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ height: '100vh', width: '100vw', display: 'flex', justifyContent: 'center', alignItems: 'center', background: '#f3f4f6', fontFamily: 'sans-serif' }}>
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
              padding: '10px 14px', borderRadius: '12px', maxWidth: '80%', fontSize: '14px', lineHeight: '1.4'
            }}>
              {msg.text}
            </div>
          ))}
          
          {loading && countdown === 0 && <div style={{ fontSize: '12px', color: '#999', marginLeft: '5px' }}>Searching payroll records...</div>}
          <div ref={scrollRef} />
        </div>

        <div style={{ padding: '15px', borderTop: '1px solid #eee', display: 'flex', gap: '10px' }}>
          <input 
            value={query} 
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendQuery()}
            placeholder={countdown > 0 ? "Please wait..." : "Ask a question..."}
            disabled={loading || countdown > 0}
            style={{ flex: 1, padding: '12px', borderRadius: '8px', border: '1px solid #ddd', outline: 'none' }}
          />
          <button 
            onClick={sendQuery} 
            disabled={loading || countdown > 0}
            style={{ padding: '10px 20px', background: (loading || countdown > 0) ? '#9ca3af' : '#4F46E5', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer' }}
          >
            {loading ? "..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;