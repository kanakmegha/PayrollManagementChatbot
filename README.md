# 📊 Smart Payroll AI Assistant (RAG Pipeline)

An automated intelligence system that allows human resources and management to "talk" to their payroll data (Excel, CSV, and PDF) using AI and Vector Search.

---

## 🌟 Executive Summary (Non-Technical)
This project builds a **"Second Brain"** for your payroll documents. Instead of searching through spreadsheets manually, you can ask the AI questions in plain English.

* **Automated Processing:** Drop a file in the "payroll" folder; the system reads and learns it instantly.
* **Multi-Format:** Supports Excel (.xlsx), CSV, and PDF.
* **Accuracy:** Uses high-density vector embeddings to provide grounded, factual answers.

---

## 🛠 Technical Architecture

### 1. The Webhook & Edge Function
This system is event-driven:
1.  **Storage Event:** A file is uploaded to the Supabase `payroll` bucket.
2.  **Database Webhook:** Supabase detects the `INSERT` in `storage.objects` and triggers an HTTP POST to the Edge Function.
3.  **Edge Function (Deno):** Downloads the file, parses it using `xlsx` or `pdf-parse`, and sends chunks to Hugging Face for 384-dimension vector embeddings.
4.  **Vector DB:** The embeddings are stored in PostgreSQL via `pgvector`.

### 2. The Chat API (FastAPI)
The frontend communicates with a FastAPI backend that performs a "Similarity Search" against the database to find relevant payroll context before generating an answer.

---

## 🚀 Setup & Deployment

### 1. Backend Setup (Supabase)
Run the following SQL to initialize your database:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE documents (
  id uuid primary key default gen_random_id(),
  content text,
  embedding vector(384),
  metadata jsonb,
  created_at timestamp with time zone default now()
);
