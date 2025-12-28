import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { motion, AnimatePresence } from "framer-motion";

function App() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([
    { role: 'ai', text: 'Welcome back! How can I assist with your payroll today?' }
  ]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  //const BACKEND_URL = "http://localhost:8000";
  const BACKEND_URL = "https://payrollmanagementchatbot.onrender.com"
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendQuery = async () => {
    if (!query.trim()) return;
    const userMsg = { role: 'user', text: query };
    setMessages((prev) => [...prev, userMsg]);
    setQuery("");
    setLoading(true);

    try {
      const res = await axios.post(`${BACKEND_URL}/chat`, { question: query });
      setMessages((prev) => [...prev, { role: 'ai', text: res.data.answer }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'ai', text: "I'm having trouble connecting to the server. Please check your backend." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ 
      height: '100vh', 
      width: '100vw',  // Ensure it covers the full width
      background: 'linear-gradient(135deg, #e0e7ff 0%, #f3f4f6 100%)',
      display: 'flex', 
      flexDirection: 'column', // Stack children vertically
      justifyContent: 'center', // Centers horizontally in a flex-column
      alignItems: 'center',     // Centers horizontally in a flex-row/column
      padding: '20px',
      boxSizing: 'border-box',
      overflow: 'hidden'       // Prevent the body from scrolling
    }}>
      {/* Your Chat Card Container */}
      <div style={{ 
        width: '100%', 
        maxWidth: '550px', // Limits the width so it looks like a chat window
        height: '85vh',
        backgroundColor: 'rgba(255, 255, 255, 0.8)',
        backdropFilter: 'blur(15px)',
        borderRadius: '28px',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 20px 40px rgba(0, 0, 0, 0.1)',
        border: '1px solid rgba(255, 255, 255, 0.4)',
      }}>
        {/* Header */}
        <div style={{ padding: '20px', textAlign: 'center', borderBottom: '1px solid rgba(0,0,0,0.05)' }}>
          <h2 style={{ margin: 0, fontSize: '1.2rem', color: '#1e293b', fontWeight: '700' }}>Payroll Hub</h2>
          <div style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: '600' }}>● AI Agent Active</div>
        </div>

        {/* Chat Feed */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <AnimatePresence>
            {messages.map((msg, i) => (
              <motion.div 
                key={i}
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.2 }}
                style={{ 
                  alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  backgroundColor: msg.role === 'user' ? '#4f46e5' : '#ffffff',
                  color: msg.role === 'user' ? '#fff' : '#1e293b',
                  padding: '12px 18px',
                  borderRadius: msg.role === 'user' ? '18px 18px 2px 18px' : '18px 18px 18px 2px',
                  fontSize: '0.95rem',
                  lineHeight: '1.5',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
                  maxWidth: '85%'
                }}
              >
                {msg.text}
              </motion.div>
            ))}
          </AnimatePresence>
          {loading && (
            <motion.div 
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              style={{ fontSize: '0.8rem', color: '#64748b', marginLeft: '5px' }}
            >
              AI is drafting a response...
            </motion.div>
          )}
          <div ref={scrollRef} />
        </div>

        {/* Input area */}
        <div style={{ padding: '20px', backgroundColor: 'rgba(255,255,255,0.5)' }}>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendQuery()}
              placeholder="Ask anything..."
              style={{
                width: '100%',
                padding: '14px 20px',
                borderRadius: '30px',
                border: 'none',
                backgroundColor: '#fff',
                boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
                outline: 'none',
                fontSize: '1rem'
              }}
            />
            <button
              onClick={sendQuery}
              style={{
                position: 'absolute',
                right: '8px',
                backgroundColor: '#4f46e5',
                color: '#white',
                border: 'none',
                borderRadius: '50%',
                width: '36px',
                height: '36px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <span style={{ color: 'white', fontWeight: 'bold' }}>↑</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;