# Developer Scripts

Utility scripts for local development. None of these run in production and none are part of the
automated test suite (see `backend/tests/` for that).

## Knowledge base maintenance

- **`rebuild_index.py`** — Rebuilds the FAISS vector store from whatever is currently in
  `./data/crawled`, `./data/structured`, and `./data/music_theory`. Run this after adding new
  source documents. Requires `OPENAI_API_KEY` (used to generate embeddings).
  ```
  python -m backend.scripts.rebuild_index
  ```
- **`run_deep_crawl.py`** — Runs `ChurchMusicCrawler` with a deeper crawl configuration
  (`max_depth=3`, `max_pages=200`) against a curated list of official Church music URLs, writing
  results to `./data/crawled`. Follow up with `rebuild_index.py` to index the new pages.

## Manual chat clients

- **`cli_chat_api.py`** — A zero-dependency terminal client that talks to a *running* backend
  over HTTP (`http://127.0.0.1:8080/chat` by default). Useful for a quick manual sanity check
  or demo without opening the frontend.
- **`cli_chat_direct.py`** — Same idea, but instantiates `RAGPipeline` in-process instead of
  going over HTTP — useful for debugging the pipeline directly. Requires `OPENAI_API_KEY`.

## `manual/`

Historical smoke-test scripts (`comprehensive_user_test.py`, `test_query.py`, `test_server.py`,
etc.). These predate the real pytest suite in `backend/tests/`: they print output rather than
assert, and most require a live server and/or a live `OPENAI_API_KEY`. They are **not** run in
CI and are kept only as manual debugging aids — prefer `backend/tests/` for anything that needs
to be verified automatically.
