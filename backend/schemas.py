"""Pydantic request/response models shared across routers."""
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    message: str = Field(..., max_length=1000)
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    sources: List[dict]
    conversation_id: str
    timestamp: str
    audio_url: Optional[str] = None
    audio_title: Optional[str] = None
    confidence: Optional[str] = None
    search_method: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
