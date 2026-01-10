# Music Assist Backend

A RAG-powered chatbot for LDS music theory, built with FastAPI, LangChain, and OpenAI.

## 📋 Prerequisites

1.  **Python 3.9+** installed.
2.  **OpenAI API Key**: You need a paid account (credits added to balance), not just ChatGPT Plus.

## 🛠️ Installation

Navigate to the backend directory:

```bash
cd backend
```

### Option A: Using Poetry (Recommended)
```bash
poetry install
```

### Option B: Using Pip (If Poetry fails)
```bash
pip install fastapi "uvicorn[standard]" langchain langchain-openai langchain-community faiss-cpu python-dotenv beautifulsoup4 lxml aiohttp
```

## ⚙️ Configuration

1.  Create a file named `.env` in the `backend` folder.
2.  Add your OpenAI API key:

```dotenv
OPENAI_API_KEY=sk-your-actual-api-key-here
LLM_MODEL=gpt-3.5-turbo
```

## 🚀 How to Run

### Step 1: Populate the Database
Before the bot can answer questions, it needs to crawl the music websites and build its memory (Vector Store).

```bash
python populate_db.py
```
*Note: This requires OpenAI API credits. If you see a 429 error, check your billing balance at platform.openai.com.*

### Step 2: Start the Server
Open a terminal and run the backend server:

```bash
python -m uvicorn main:app --reload
```
*The server will start at `http://127.0.0.1:8000`.*

### Step 3: Chat with the Bot
Open a **new** terminal window (keep the server running in the first one) and run the chat script:

```bash
python terminal_chat.py
```

## 🔧 Troubleshooting

**Error: `ModuleNotFoundError: No module named 'langchain' ...`**
- Run the pip install command in the Installation section above to ensure all packages are present.

**Error: `insufficient_quota` or `429`**
- Your OpenAI API key is valid, but the account has no funds.
- Go to OpenAI Billing and add credits (e.g., $5).

**Error: `Vector store not initialized`**
- The database is empty. Run `python populate_db.py` to fix this.

**Error: `UnicodeDecodeError`**
- Ensure you are using the latest version of `rag_pipeline.py` which forces UTF-8 encoding when reading crawled files.