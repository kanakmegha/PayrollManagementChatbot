import { useState, useEffect, useRef } from "react";

import axios from "axios";

import { motion, AnimatePresence } from "framer-motion";



function App() {

  const [query, setQuery] = useState("");

  const [messages, setMessages] = useState([

    { role: 'ai', text: 'Hello! Ask me anything about payroll.' }

  ]);

  const [loading, setLoading] = useState(false);

  const scrollRef = useRef(null);



  const BACKEND_URL = "http://localhost:8000";



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

      // Added a 30-second timeout so it doesn't spin forever

      const res = await axios.post(`${BACKEND_URL}/chat`, 

        { question: query },

        { timeout: 30000 } 

      );

      

      setMessages((prev) => [...prev, { role: 'ai', text: res.data.answer }]);

    } catch (err) {

      console.error(err);

      setMessages((prev) => [...prev, { role: 'ai', text: "Server is too slow or offline. Check terminal." }]);

    } finally {

      // THIS IS THE FIX: Always stop loading, even on error

      setLoading(false);

    }

  };



  return (

    <div style={{ 

      height: '100vh', width: '100vw', display: 'flex', 

      justifyContent: 'center', alignItems: 'center',

      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',

      fontFamily: 'system-ui, sans-serif'

    }}>

      <div style={{ 

        width: '90%', maxWidth: '500px', height: '80vh', 

        backgroundColor: 'rgba(255, 255, 255, 0.9)', 

        borderRadius: '24px', display: 'flex', flexDirection: 'column', 

        boxShadow: '0 10px 30px rgba(0,0,0,0.2)', overflow: 'hidden' 

      }}>

        

        {/* Header */}

        <div style={{ padding: '20px', background: '#fff', borderBottom: '1px solid #eee', textAlign: 'center' }}>

          <h3 style={{ margin: 0 }}>Payroll AI</h3>

        </div>



        {/* Chat Area */}

        <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '10px' }}>

          <AnimatePresence>

            {messages.map((msg, i) => (

              <motion.div 

                key={i}

                initial={{ opacity: 0, y: 10 }}

                animate={{ opacity: 1, y: 0 }}

                style={{ 

                  alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',

                  backgroundColor: msg.role === 'user' ? '#4F46E5' : '#E5E7EB',

                  color: msg.role === 'user' ? '#fff' : '#000',

                  padding: '10px 15px', borderRadius: '15px', maxWidth: '80%'

                }}

              >

                {msg.text}

              </motion.div>

            ))}

          </AnimatePresence>

          {loading && (

            <motion.div animate={{ opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity }} style={{ fontSize: '12px', color: '#667' }}>

              AI is drafting a response...

            </motion.div>

          )}

          <div ref={scrollRef} />

        </div>



        {/* Input */}

        <div style={{ padding: '20px', borderTop: '1px solid #eee' }}>

          <div style={{ display: 'flex', gap: '10px' }}>

            <input 

              value={query} 

              onChange={(e) => setQuery(e.target.value)}

              onKeyDown={(e) => e.key === 'Enter' && sendQuery()}

              placeholder="Ask a question..."

              style={{ flex: 1, padding: '10px', borderRadius: '10px', border: '1px solid #ddd' }}

            />

            <button onClick={sendQuery} style={{ padding: '10px', background: '#4F46E5', color: '#fff', border: 'none', borderRadius: '10px' }}>

              Send

            </button>

          </div>

        </div>

      </div>

    </div>

  );

}



export default App;