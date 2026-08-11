"""Conversation history endpoints, backed by whichever memory implementation
RAGPipeline was configured with."""
import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends

from dependencies import get_rag_pipeline_optional
from rag_pipeline import RAGPipeline

router = APIRouter(tags=["conversations"])


@router.get("/conversations/{user_id}")
async def get_user_conversations(
    user_id: str,
    rag_pipeline: Optional[RAGPipeline] = Depends(get_rag_pipeline_optional),
):
    """List past conversations for a user"""
    if not rag_pipeline or not rag_pipeline.memory:
        return []

    raw_convs = await asyncio.to_thread(rag_pipeline.memory.get_user_conversations, user_id)

    conversations = []
    for c in raw_convs:
        ts = c.get("last_updated")
        # Convert Firestore timestamp to numeric milliseconds
        numeric_ts = int(ts.timestamp() * 1000) if hasattr(ts, "timestamp") else 0

        conversations.append({
            "id": c["id"],
            "title": c["title"],
            "last_updated": numeric_ts,
        })

    return conversations


@router.get("/conversations/{conversation_id}/history")
async def get_conversation_history(
    conversation_id: str,
    rag_pipeline: Optional[RAGPipeline] = Depends(get_rag_pipeline_optional),
):
    """Retrieve full message history for a specific conversation"""
    if not rag_pipeline or not rag_pipeline.memory:
        return []

    raw_history = await asyncio.to_thread(rag_pipeline.memory.get_history, conversation_id)

    formatted = []
    base_ts = int(datetime.now(timezone.utc).timestamp() * 1000)

    for i, (q, a) in enumerate(raw_history):
        formatted.append({
            "id": f"{conversation_id}_{i}_q",
            "sender": "user",
            "text": q,
            "timestamp": base_ts + (i * 2),
        })
        formatted.append({
            "id": f"{conversation_id}_{i}_a",
            "sender": "ai",
            "text": a,
            "timestamp": base_ts + (i * 2) + 1,
            "sources": [],
        })
    return formatted
