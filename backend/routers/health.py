"""Liveness/readiness/stats endpoints."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from dependencies import get_rag_pipeline, get_rag_pipeline_optional
from rag_pipeline import RAGPipeline
from schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/", response_model=HealthResponse)
async def root():
    """Liveness probe - always healthy once the process is up."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
    )


@router.get("/health", response_model=HealthResponse)
async def health_check(
    rag_pipeline: Optional[RAGPipeline] = Depends(get_rag_pipeline_optional),
):
    """Readiness probe - reflects the real state of the RAG pipeline's dependencies."""
    status = "unhealthy"
    if rag_pipeline is not None:
        result = await rag_pipeline.health_check()
        status = result.get("status", "unhealthy")

    return HealthResponse(
        status=status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
    )


@router.get("/stats")
async def get_stats(rag_pipeline: RAGPipeline = Depends(get_rag_pipeline)):
    """Get system statistics"""
    try:
        stats = await rag_pipeline.get_stats()
        return {
            "status": "success",
            "statistics": stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")
