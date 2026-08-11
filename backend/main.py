"""
Music-Assist Backend API
FastAPI application with RAG pipeline for LDS music theory chatbot.

This module wires the app together (lifespan, CORS, routers). Route logic
lives in routers/, shared config in config.py, and cross-cutting services in
services/ - see backend/README.md for the full module map.
"""
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

from logging_config import setup_logging
import structlog

setup_logging()
logger = structlog.get_logger(__name__)

from config import settings
from rag_pipeline import RAGPipeline
from rate_limit import limiter
from routers import admin, chat, conversations, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.rag_pipeline = None

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
