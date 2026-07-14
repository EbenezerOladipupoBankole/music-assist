"""
FastAPI dependency providers.

RAGPipeline / HymnPlayer / AudioCacheManager are initialized once in main.py's
lifespan and stored on `app.state`, rather than as module-level globals. These
functions are the single place that knows how to fetch them back out for a
route handler via `Depends(...)`.
"""
from typing import Optional

from fastapi import HTTPException, Request

from audio_manager import AudioCacheManager
from hymn_player import HymnPlayer
from rag_pipeline import RAGPipeline


def get_rag_pipeline_optional(request: Request) -> Optional[RAGPipeline]:
    return getattr(request.app.state, "rag_pipeline", None)


def get_rag_pipeline(request: Request) -> RAGPipeline:
    rag_pipeline = get_rag_pipeline_optional(request)
    if rag_pipeline is None:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
    return rag_pipeline


def get_hymn_player(request: Request) -> Optional[HymnPlayer]:
    return getattr(request.app.state, "hymn_player", None)


def get_audio_cache(request: Request) -> Optional[AudioCacheManager]:
    return getattr(request.app.state, "audio_cache", None)
