"""Pydantic request/response models shared across routers."""
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    message: str = Field(..., max_length=1000)
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None


class SourceItem(BaseModel):
    """A single citation entry returned alongside a chat response."""
    type: str  # 'local' | 'web'
    title: str
    source: Optional[str] = None   # local-source URL / identifier
    url: Optional[str] = None      # web-source URL
    relevance: Optional[float] = None  # web-source relevance score (0–1)


class ChatResponse(BaseModel):
    response: str
    sources: List[SourceItem]
    conversation_id: str
    timestamp: str
    confidence: Optional[str] = None
    search_method: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
