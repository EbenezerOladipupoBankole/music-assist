"""
Music-Assist Backend API
FastAPI application with RAG pipeline for LDS music theory chatbot.

This module wires the app together (lifespan, CORS, routers). Route logic
lives in routers/, shared config in config.py, and cross-cutting services in
services/ - see backend/README.md for the full module map.
"""
import logging
import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Ensure local imports (rag_pipeline, routers, etc.) work regardless of cwd
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from audio_manager import AudioCacheManager
from config import settings
from hymn_player import HymnPlayer
from rag_pipeline import RAGPipeline
from rate_limit import limiter
from routers import admin, audio, chat, conversations, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.audio_cache = None
    app.state.rag_pipeline = None
    app.state.hymn_player = None

    # 1. Init Local Audio Cache
    try:
        app.state.audio_cache = AudioCacheManager()
    except Exception:
        logger.error("AudioCache failed to initialize", exc_info=True)

    # 2. Init RAG (SQLite Memory inside)
    try:
        rag_pipeline = RAGPipeline(
            vector_db_path=settings.vector_db_path,
            model_name=settings.llm_model,
        )
        await rag_pipeline.initialize()
        app.state.rag_pipeline = rag_pipeline
        logger.info("[OK] RAG & Memory Ready")
    except Exception:
        logger.error("RAG initialization failed", exc_info=True)

    # 3. Init Hymn Data
    try:
        app.state.hymn_player = HymnPlayer()
        logger.info("[OK] HymnPlayer Ready")
    except Exception:
        logger.error("HymnPlayer failed to initialize", exc_info=True)

    yield


# Initialize FastAPI app
app = FastAPI(
    title="Music-Assist API",
    description="Offline-ready RAG chatbot for Church music",
    version="1.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.default_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(audio.router)
app.include_router(conversations.router)
app.include_router(admin.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=settings.port,
        reload=True,
    )
