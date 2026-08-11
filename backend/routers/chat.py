"""Chat endpoints: standard request/response and streaming.

Both endpoints share the same intent-detection rules (services/intent.py) for
canned greetings, falling through to the full RAG
pipeline for everything else.
"""
import asyncio
import json
import structlog
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from dependencies import get_rag_pipeline, get_rag_pipeline_optional
from rag_pipeline import RAGPipeline
from rate_limit import limiter
from schemas import ChatMessage, ChatResponse
from services.intent import (
    first_name,
    is_greeting,
    is_how_are_you,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["chat"])





@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(
    request: Request,
    message: ChatMessage,
    rag_pipeline: Optional[RAGPipeline] = Depends(get_rag_pipeline_optional),
):
    """Main chat endpoint - processes user queries with RAG."""
    try:
        uid = message.user_id
        cid = message.conversation_id or f"conv_{int(datetime.now(timezone.utc).timestamp())}"
        user_msg = message.message.lower().strip()

        logger.info("incoming_chat_request", uid=uid, cid=cid, query_length=len(user_msg))



        # 2. Check for Greetings
        if is_greeting(user_msg):
            name_part = f" {first_name(message.user_name)}" if message.user_name else ""
            resp = f"Hi{name_part}! I am Music-Assist. How can I help you with Church music today?"

            if rag_pipeline and rag_pipeline.memory:
                await asyncio.to_thread(rag_pipeline.memory.add_message, cid, message.message, resp, uid)

            return ChatResponse(
                response=resp,
                sources=[],
                conversation_id=cid,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        # 3. Check for "How are you" type questions
        if is_how_are_you(user_msg):
            name_part = f" {first_name(message.user_name)}" if message.user_name else ""
            resp = (
                f"I'm doing well, thank you{name_part}! I'm here and ready to help you with "
                "Church music questions, hymn searches, conducting guidance, or music theory. "
                "What would you like to explore today?"
            )

            if rag_pipeline and rag_pipeline.memory:
                await asyncio.to_thread(rag_pipeline.memory.add_message, cid, message.message, resp, uid)

            return ChatResponse(
                response=resp,
                sources=[],
                conversation_id=cid,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        if not rag_pipeline:
            raise HTTPException(status_code=503, detail="RAG pipeline not initialized")

        # Process the query through RAG pipeline (this now handles saving for standard queries)
        result = await rag_pipeline.query(
            query=message.message,
            conversation_id=cid,
            user_id=uid,
        )

        return ChatResponse(
            response=result["answer"] if result.get("answer") else "I found some relevant sources but couldn't generate a specific answer.",
            sources=result["sources"],
            conversation_id=result["conversation_id"],
            timestamp=datetime.now(timezone.utc).isoformat(),
            confidence=result.get("confidence"),
            search_method=result.get("search_method"),
        )

    except HTTPException:
        raise
    except Exception:
        logger.error("chat_query_error", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred while processing your query.")


@router.post("/chat/stream")
@limiter.limit("20/minute")
async def chat_stream(
    request: Request,
    message: ChatMessage,
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline),
):
    """Streaming chat endpoint for real-time AI responses."""
    cid = message.conversation_id
    uid = message.user_id
    user_msg = message.message.lower().strip()

    async def event_generator():

        # 2. Check for Greetings / "how are you" - same canned responses as
        # the non-streaming /chat endpoint (see services/intent.py).
        canned_resp = None
        if is_greeting(user_msg):
            name_part = f" {first_name(message.user_name)}" if message.user_name else ""
            canned_resp = f"Hi{name_part}! I am Music-Assist. How can I help you with Church music today?"
        elif is_how_are_you(user_msg):
            name_part = f" {first_name(message.user_name)}" if message.user_name else ""
            canned_resp = (
                f"I'm doing well, thank you{name_part}! I'm here and ready to help you with "
                "Church music questions, hymn searches, conducting guidance, or music theory. "
                "What would you like to explore today?"
            )

        if canned_resp is not None:
            final_cid = cid or f"conv_{int(datetime.now(timezone.utc).timestamp())}"
            yield json.dumps({"type": "metadata", "conversation_id": final_cid, "sources": []}) + "\n"
            yield json.dumps({"type": "content", "delta": canned_resp}) + "\n"

            if rag_pipeline.memory:
                await asyncio.to_thread(
                    rag_pipeline.memory.add_message, final_cid, message.message, canned_resp, uid
                )
            return

        try:
            async for chunk in rag_pipeline.stream_query(message.message, cid, uid):
                yield f"{chunk}\n"
        except Exception:
            logger.error("chat_stream_error", exc_info=True)
            yield json.dumps({"type": "error", "message": "Internal streaming error occurred."}) + "\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
