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

### Option B: Using Pip
```bash
# Create virtual environment
python -m venv venv

# Activate it (Windows):
.\venv\Scripts\activate

# Activate it (macOS/Linux):
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn python-multipart pydantic langchain langchain-openai langchain-community langchain-text-splitters openai faiss-cpu aiohttp beautifulsoup4 lxml numpy pandas python-dotenv firebase-admin python-json-logger
```

## ⚙️ Configuration

1.  Copy the environment template:
```bash
cp .env.example .env
```

2.  Edit `.env` and add your keys:
```dotenv
OPENAI_API_KEY=sk-your-actual-api-key-here
ADMIN_KEY=your-secure-admin-key
LLM_MODEL=gpt-3.5-turbo
VECTOR_DB_PATH=./data/vector_store
CRAWLED_DATA_PATH=./data/crawled
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
```

**Getting your OpenAI API Key:**
1. Go to https://platform.openai.com/account/api-keys
2. Create a new API key
3. Add credits to your account (need $$ balance, not just ChatGPT Plus)
4. Copy the key into your `.env` file

## 🚀 How to Run

### Step 1: Populate the Database (First Time Only)
Before the bot can answer questions, it needs to crawl the music websites and build its memory (Vector Store).

```bash
python crawler.py
```
*Note: This requires OpenAI API credits. If you see a 429 error, check your billing balance at platform.openai.com.*

### Step 2: Start the Server
Open a terminal and run the backend server:

```bash
# If using virtual environment, activate it first:
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Start server
python -m uvicorn main:app --reload --port 8000
```
*The server will start at `http://127.0.0.1:8000`*
*API docs available at `http://127.0.0.1:8000/docs`*

### Step 3: Chat with the Bot (Optional)
Open a **new** terminal window (keep the server running in the first one) and run the chat script:

```bash
python terminal_chat.py
```

## 🔧 Troubleshooting

**Error: `ModuleNotFoundError: No module named 'langchain' ...`**
- Ensure you've activated your virtual environment and installed all dependencies
- Windows: `.\venv\Scripts\activate` then `pip install -r requirements.txt`
- macOS/Linux: `source venv/bin/activate` then `pip install -r requirements.txt`

**Error: `insufficient_quota` or `429`**
- Your OpenAI API key is valid, but the account has no funds.
- Go to https://platform.openai.com/account/billing/overview
- Add credits (e.g., $5) to your account
- Wait a few minutes for changes to propagate

**Error: `Vector store not initialized`**
- The database is empty. Run `python crawler.py` to populate it
- Make sure your `.env` file has a valid `OPENAI_API_KEY` with credits

**Error: `OPENAI_API_KEY not found`**
- Ensure `.env` file exists in the `backend` directory
- Check that `OPENAI_API_KEY=sk-...` is on the first line
- Make sure there are no extra spaces or quotes

**Error: `UnicodeDecodeError`**
- Ensure you're using the latest version of the code
- Delete and re-run `python crawler.py`

**Server won't start or keeps reloading**
- Check if port 8000 is already in use
- Try a different port: `python -m uvicorn main:app --reload --port 8001`

## 📝 For Collaborators

To get the latest changes:

```bash
# Pull latest code
git pull origin main

# Make sure virtual environment is set up
python -m venv venv
.\venv\Scripts\activate  # Windows

# Install/update dependencies
pip install -r requirements.txt
# Or if using the pip install command from above

# Configure your .env file if it doesn't exist
cp .env.example .env
# Edit .env with your own API keys

# You're ready to go!
python -m uvicorn main:app --reload
```