"""Chat endpoints: standard request/response and streaming.

Both endpoints share the same intent-detection rules (services/intent.py) for
canned greetings and hymn-audio requests, falling through to the full RAG
pipeline for everything else.
"""
import asyncio
import json
import logging
import random
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from dependencies import get_hymn_player, get_rag_pipeline, get_rag_pipeline_optional
from hymn_player import HymnPlayer
from rag_pipeline import RAGPipeline
from rate_limit import limiter
from schemas import ChatMessage, ChatResponse
from services.intent import (
    first_name,
    is_explicit_random_request,
    is_greeting,
    is_how_are_you,
    resolve_hymn_query,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


def _pick_hymn(hymn_player: HymnPlayer, query: str) -> Optional[dict]:
    """Resolve a hymn search query to a single hymn, falling back to a random
    pick if the user explicitly asked for "something"/"random"."""
    hymns = hymn_player.get_hymns(query)
    if not hymns and is_explicit_random_request(query):
        hymns = [random.choice(hymn_player.hymns_db)]
    return hymns[0] if hymns else None


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(
    request: Request,
    message: ChatMessage,
    rag_pipeline: Optional[RAGPipeline] = Depends(get_rag_pipeline_optional),
    hymn_player: Optional[HymnPlayer] = Depends(get_hymn_player),
):
    """Main chat endpoint - processes user queries with RAG."""
    try:
        uid = message.user_id
        cid = message.conversation_id or f"conv_{int(datetime.utcnow().timestamp())}"
        user_msg = message.message.lower().strip()

        logger.info(f"Incoming chat request: UID={uid}, CID={cid}, Message='{user_msg[:30]}...'")

        # 1. Check for Hymn Audio Request (Typo resilient)
        hymn_query = resolve_hymn_query(user_msg) if hymn_player else None
        if hymn_query is not None:
            primary_hymn = _pick_hymn(hymn_player, hymn_query)

            if primary_hymn:
                if primary_hymn.get("url") is None:
                    access_note = primary_hymn.get(
                        "access_note",
                        "Access hymn audio via Gospel Library app or ChurchofJesusChrist.org/music",
                    )
                    response_text = (
                        f"**{primary_hymn['title']}** (Hymn #{primary_hymn['number']})\n\n"
                        f"📱 **How to Listen:**\n{access_note}\n\n"
                        "*Note: Direct audio playback is temporarily unavailable due to updates "
                        "in the Church's media delivery system. The audio recordings are still "
                        "available through the official Church apps and website.*"
                    )

                    if rag_pipeline and rag_pipeline.memory:
                        await asyncio.to_thread(
                            rag_pipeline.memory.add_message, cid, message.message, response_text, uid
                        )

                    return ChatResponse(
                        response=response_text,
                        sources=[{
                            "type": "external",
                            "title": "Gospel Library App",
                            "url": "https://www.churchofjesuschrist.org/media/music",
                        }],
                        conversation_id=cid,
                        timestamp=datetime.utcnow().isoformat(),
                    )
                else:
                    response_text = (
                        f"I've retrieved the official recording for "
                        f"**\"{primary_hymn['title']}\"** (Hymn #{primary_hymn['number']})."
                    )

                    if rag_pipeline and rag_pipeline.memory:
                        await asyncio.to_thread(
                            rag_pipeline.memory.add_message, cid, message.message, response_text, uid
                        )

                    return ChatResponse(
                        response=response_text,
                        sources=[],
                        conversation_id=cid,
                        timestamp=datetime.utcnow().isoformat(),
                        audio_url=f"/audio/hymn/{primary_hymn['number']}",
                        audio_title=f"{primary_hymn['title']} (#{primary_hymn['number']})",
                    )

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
                timestamp=datetime.utcnow().isoformat(),
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
                timestamp=datetime.utcnow().isoformat(),
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
            timestamp=datetime.utcnow().isoformat(),
            confidence=result.get("confidence"),
            search_method=result.get("search_method"),
        )

    except HTTPException:
        raise
    except Exception:
        logger.error("Error processing chat query", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred while processing your query.")


@router.post("/chat/stream")
@limiter.limit("20/minute")
async def chat_stream(
    request: Request,
    message: ChatMessage,
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline),
    hymn_player: Optional[HymnPlayer] = Depends(get_hymn_player),
):
    """Streaming chat endpoint for real-time AI responses."""
    cid = message.conversation_id
    uid = message.user_id
    user_msg = message.message.lower().strip()

    # 1. Check for audio intent in streaming too
    hymn_query = resolve_hymn_query(user_msg) if hymn_player else None

    async def event_generator():
        if hymn_query is not None:
            primary_hymn = _pick_hymn(hymn_player, hymn_query)

            if primary_hymn:
                final_cid = cid or f"conv_{int(datetime.utcnow().timestamp())}"

                if primary_hymn.get("url") is None:
                    access_note = primary_hymn.get(
                        "access_note", "Access via Gospel Library app or ChurchofJesusChrist.org/music"
                    )
                    resp_text = (
                        f"**{primary_hymn['title']}** (Hymn #{primary_hymn['number']})\n\n"
                        f"📱 **How to Listen:**\n{access_note}\n\n"
                        "*Note: Direct audio playback is temporarily unavailable due to updates "
                        "in the Church's media delivery system.*"
                    )

                    yield json.dumps({
                        "type": "metadata",
                        "conversation_id": final_cid,
                        "sources": [{
                            "type": "external",
                            "title": "Gospel Library App",
                            "url": "https://www.churchofjesuschrist.org/media/music",
                        }],
                    }) + "\n"
                    yield json.dumps({"type": "content", "delta": resp_text}) + "\n"

                    if rag_pipeline.memory:
                        await asyncio.to_thread(
                            rag_pipeline.memory.add_message, final_cid, message.message, resp_text, uid
                        )
                    return
                else:
                    audio_title = f"{primary_hymn['title']} (#{primary_hymn['number']})"
                    resp_text = (
                        f"I've retrieved the official recording for "
                        f"**\"{primary_hymn['title']}\"** (Hymn #{primary_hymn['number']})."
                    )

                    yield json.dumps({
                        "type": "metadata",
                        "audio_url": f"/audio/hymn/{primary_hymn['number']}",
                        "audio_title": audio_title,
                        "conversation_id": final_cid,
                    }) + "\n"
                    yield json.dumps({"type": "content", "delta": resp_text}) + "\n"

                    if rag_pipeline.memory:
                        await asyncio.to_thread(
                            rag_pipeline.memory.add_message, final_cid, message.message, resp_text, uid
                        )
                    return

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
            final_cid = cid or f"conv_{int(datetime.utcnow().timestamp())}"
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
            logger.error("Error during chat stream", exc_info=True)
            yield json.dumps({"type": "error", "message": "Internal streaming error occurred."}) + "\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
