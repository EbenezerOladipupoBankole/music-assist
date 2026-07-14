"""
Structural typing contracts shared across interchangeable backend components.

RAGPipeline accepts either SQLiteConversationMemory or FirebaseConversationMemory
as its `memory` backend. Neither inherits from a common base class today, so
nothing stops the two implementations from silently drifting apart. This
Protocol pins down the contract both must satisfy; a type checker will flag
either implementation if it stops matching.
"""
from typing import List, Optional, Protocol, Tuple


class ConversationMemory(Protocol):
    def get_history(self, conversation_id: str) -> List[Tuple[str, str]]:
        ...

    def add_message(
        self,
        conversation_id: str,
        user_query: str,
        ai_response: str,
        user_id: Optional[str] = None,
    ) -> None:
        ...

    def get_user_conversations(self, user_id: str) -> List[dict]:
        ...
