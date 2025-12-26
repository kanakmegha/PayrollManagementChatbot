import { useState } from "react";
import axios from "axios";

function App() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);

  // ⚠️ Change this to your Render backend URL http://localhost:8000" 
  const BACKEND_URL = "https://payrollmanagementchatbot.onrender.com";
  const sendQuery = async () => {
    if (!query.trim()) return;

    setLoading(true);

    try {
      const res = await axios.post(`${BACKEND_URL}/query`, { query });
      setResponse(res.data.answer);
    } catch (err) {
      setResponse("Error: Backend not reachable");
      console.error(err);
    }

    setLoading(false);
  };

  return (
    <div style={{ maxWidth: "600px", margin: "0 auto", padding: "20px" }}>
      <h1>Payroll Management Chatbot</h1>

      <textarea
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Ask your question..."
        style={{
          width: "100%",
          height: "120px",
          padding: "10px",
          marginTop: "20px",
          borderRadius: "8px",
          border: "1px solid #ccc",
        }}
      />

      <button
        onClick={sendQuery}
        disabled={loading}
        style={{
          marginTop: "10px",
          padding: "10px 20px",
          borderRadius: "8px",
          cursor: "pointer",
        }}
      >
        {loading ? "Thinking..." : "Send"}
      </button>

      {response && (
        <div
          style={{
            marginTop: "20px",
            padding: "15px",
            background: "#f4f4f4",
            borderRadius: "8px",
          }}
        >
          <strong>Response:</strong>
          <p>{response}</p>
        </div>
      )}
    </div>
  );
}

export default App;
