import { useState, useEffect, useRef } from "react";
import axios from "axios";

function App() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([
    { role: 'ai', text: 'Hello! Ask me anything about payroll.' }
  ]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  const BACKEND_URL = "https://payrollmanagementchatbot.onrender.com";

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendQuery = async () => {
    if (!query.trim() || loading) return;

    const userMsg = { role: 'user', text: query };
    setMessages((prev) => [...prev, userMsg]);
    setQuery("");
    setLoading(true);

    try {
      // Increased timeout to 60s to handle Render's "Cold Start"
      const res = await axios.post(`${BACKEND_URL}/chat`, 
        { question: query },
        { timeout: 60000 } 
      );
      setMessages((prev) => [...prev, { role: 'ai', text: res.data.answer }]);
    } catch (err) {
      setMessages((prev) => [...prev, { 
        role: 'ai', 
        text: "The server is taking a moment to wake up. Please wait 10 seconds and try again." 
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ height: '100vh', width: '100vw', display: 'flex', justifyContent: 'center', alignItems: 'center', background: '#f3f4f6' }}>
      <div style={{ width: '95%', maxWidth: '500px', height: '85vh', backgroundColor: '#fff', borderRadius: '15px', display: 'flex', flexDirection: 'column', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
        
        <div style={{ padding: '15px', borderBottom: '1px solid #eee', fontWeight: 'bold', color: '#4F46E5' }}>Payroll AI Support</div>

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
          {loading && <div style={{ fontSize: '12px', color: '#999' }}>AI is thinking...</div>}
          <div ref={scrollRef} />
        </div>

        <div style={{ padding: '15px', borderTop: '1px solid #eee', display: 'flex', gap: '10px' }}>
          <input 
            value={query} 
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendQuery()}
            placeholder="Ask a question..."
            style={{ flex: 1, padding: '10px', borderRadius: '8px', border: '1px solid #ddd' }}
          />
          <button onClick={sendQuery} style={{ padding: '10px 20px', background: '#4F46E5', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer' }}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;