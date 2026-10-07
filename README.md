# LY-proj-Flask

# 🧠 Student AI Assistant

A Flask-based AI assistant that integrates with OpenAI's GPT models and stores data in MongoDB.

# 🤖 AI Study Assistant

An AI-powered study assistant that lets students **ask questions directly from their study material** using Retrieval-Augmented Generation (RAG).

## 🚀 Features

- 📄 Upload and process study PDFs/notes
- 🔍 Semantic search using vector embeddings
- 📚 Subject-wise FAISS vector databases
- 🖼️ OCR support for scanned documents
- 💬 Context-aware question answering
- 🧠 RAG-based responses grounded in uploaded content

## 🛠️ Tech Stack

**Python • LangChain • FAISS • Sentence Transformers • Tesseract OCR • LLMs**

### 🔄 Workflow

```text
PDF / Notes
    ↓
Text Extraction + OCR
    ↓
Chunking
    ↓
Embeddings
    ↓
FAISS Vector Store
    ↓
User Query
    ↓
Relevant Context Retrieval
    ↓
LLM
    ↓
Answer
```

## 🧠 Embedding Models

- `all-MiniLM-L6-v2`
- `paraphrase-multilingual-MiniLM-L12-v2`

## 🎯 Problem Solved

Students often spend significant time searching through lengthy PDFs and notes. This project enables them to **ask questions in natural language and receive answers based on their own study material**.

## 🔮 Future Scope

- Page-level citations
- Hybrid search
- Quiz & flashcard generation
- Conversation memory
- Personalized study plans

---

## 📁 Environment Setup

This project uses environment variables for sensitive configuration. Create a `.env` file in the root of the project directory with the following contents:

```env
# .env

FLASK_ENV=student-ai-assistant
MONGO_URI=your_uri
SECRET_KEY=studentassistant
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini
UPLOAD_FOLDER=uploads
