# Music Assist Backend

A RAG-powered chatbot for LDS Church music (hymns, conducting, music theory, and
music-calling guidance), built with FastAPI, LangChain, OpenAI, and FAISS.

## Architecture

```
main.py            FastAPI app: lifespan (wires up RAGPipeline/HymnPlayer),
                    CORS, router registration.
config.py           Centralized Settings (pydantic-settings) - every env var
                    the backend reads lives here.
dependencies.py     FastAPI DI providers that pull the app.state singletons
                    back out for route handlers.
interfaces.py       ConversationMemory Protocol shared by the SQLite and
                    Firestore memory backends.
routers/            One module per resource: health, chat,
                    conversations, admin.
services/intent.py  Regex-based canned-response detection (greetings, "how
                    are you") shared by /chat and
                    /chat/stream so they can't drift apart.
rag_pipeline.py      Core RAG engine: FAISS retrieval + web-search fallback +
                    OpenAI generation + conversation-aware caching.
sqlite_memory.py /
firebase_memory.py  Conversation history backends (selected via
                    settings.memory_backend, default sqlite).
web_search.py        Fallback search over a fixed set of Church music pages
                    when the local vector store is thin.
crawler.py / populate_db.py
                    Offline scripts to build the FAISS index from Church
                    websites + structured hymn/theory data.
```

## Prerequisites

- Python 3.11+
- An OpenAI API key with billing enabled (a ChatGPT Plus subscription alone
  does **not** grant API access)

## Setup

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate      # Windows
source venv/bin/activate     # macOS/Linux

pip install -r requirements-dev.txt   # requirements.txt + pytest/ruff
cp .env.example .env
# edit .env: set OPENAI_API_KEY and ADMIN_KEY at minimum
```

## Build the knowledge base (first run only)

The bot answers from a local FAISS index built from Church websites and
structured hymn/theory data. Build it once before starting the server:

```bash
python populate_db.py
```

This crawls the configured Church music pages (`crawler.py`) and then builds
the FAISS index (`rag_pipeline.rebuild_vector_store`) - expect this to take
several minutes and to spend OpenAI embedding credits. Until this has run
once, `/chat` responds with a "Knowledge Base Not Initialized" message
instead of an error.

## Run the server

```bash
python -m uvicorn main:app --reload --port 8080
```

- API: `http://127.0.0.1:8080`
- Interactive docs: `http://127.0.0.1:8080/docs`

## API surface

| Endpoint | Notes |
|---|---|
| `GET /` , `GET /health` | Liveness / readiness (reflects RAG pipeline health) |
| `GET /stats` | Query counts, cost tracking, success rate |
| `POST /chat` | Single-shot chat response |
| `POST /chat/stream` | NDJSON-streamed chat response |
| `GET /conversations/{user_id}` | List a user's past conversations |
| `GET /conversations/{conversation_id}/history` | Full message history for one conversation |
| `POST /crawl/trigger` | Admin-only: re-crawl + rebuild the index (`admin_key` query param) |
| `GET /debug/memory` | Admin-only: conversation-memory diagnostics |

`/chat` and `/chat/stream` short-circuit to canned responses (see
`services/intent.py`) for greetings and "how are you"
before falling through to the full RAG pipeline for everything else.
Off-topic (non-music) questions get a fixed redirect message rather than
being sent to the LLM.

## Testing

```bash
pytest              # full suite - runs offline, no OpenAI key needed
ruff check .         # lint
```

The suite (`tests/`) fakes out the RAG pipeline and hymn player
via FastAPI `dependency_overrides` (see `tests/conftest.py`), so it never
makes a real OpenAI/Firestore call.

## Troubleshooting

**`ModuleNotFoundError: No module named 'langchain'`**
Activate the virtualenv, then `pip install -r requirements.txt`.

**`insufficient_quota` / HTTP 429 from OpenAI**
The API key is valid but the account has no funds. Add credits at
https://platform.openai.com/settings/organization/billing and wait a few
minutes.

**Chat replies with "Knowledge Base Not Initialized"**
The FAISS index hasn't been built yet - run `python populate_db.py`.

**`OPENAI_API_KEY` not found**
Confirm `.env` exists in `backend/` (not the repo root) and contains
`OPENAI_API_KEY=sk-...` with no surrounding quotes.

## Deployment

Deployed on Render as a Docker web service - see `render.yaml` and
`Dockerfile`. The frontend is a separate static Firebase Hosting deploy (see
`../firebase.json`), not part of this service.
