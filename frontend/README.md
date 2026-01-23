# Music-Assist Frontend

React + TypeScript frontend for the Music-Assist RAG chatbot powered by FastAPI backend.

## Run Locally

**Prerequisites:** Node.js

1. Install dependencies:
   ```bash
   npm install
   ```
2. Start the dev server:
   ```bash
   npm run dev
   ```
3. Make sure the FastAPI backend is running on `http://localhost:8080`

The app will be available at `http://localhost:3000` (or another port if 3000 is in use).

## Architecture

- **Frontend:** React 19 with TypeScript and Tailwind CSS
- **API Service:** Communicates with FastAPI backend at `http://localhost:8080/chat`
- **Backend:** FastAPI with RAG pipeline using OpenAI LLM and FAISS vector store
