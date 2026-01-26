"""
Conversation Memory Module using Firebase Firestore
"""

import os
import firebase_admin
from firebase_admin import credentials, firestore
from typing import List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get MAX_CONVERSATION_HISTORY from rag_pipeline config
try:
    from rag_pipeline import CONFIG
    MAX_CONVERSATION_HISTORY = CONFIG.get('MAX_CONVERSATION_HISTORY', 10)
except (ImportError, KeyError):
    MAX_CONVERSATION_HISTORY = 10


class FirebaseConversationMemory:
    """
    Manages conversation history using Google Firestore.
    Falls back to in-memory storage if Firebase is not configured.
    """
    def __init__(self):
        self.db = None
        try:
            # Ensure app is initialized (should be done by main.py)
            if not firebase_admin._apps:
                firebase_admin.initialize_app()
            
            self.db = firestore.client()
            logger.info("✅ Firebase Firestore initialized successfully for conversation memory.")
        except Exception as e:
            logger.warning(f"🔥 Firebase initialization failed: {e}")
            logger.warning("Conversation memory will be IN-MEMORY ONLY.")
            self.db = None # Fallback to in-memory
            self._in_memory_fallback = {}

    def get_history(self, conversation_id: str) -> List[Tuple[str, str]]:
        """Retrieve conversation history."""
        if not self.db: # Fallback
            return self._in_memory_fallback.get(conversation_id, [])

        try:
            docs = self.db.collection('conversations').document(conversation_id).collection('messages') \
                .order_by('timestamp', direction=firestore.Query.DESCENDING) \
                .limit(MAX_CONVERSATION_HISTORY).stream()
            
            history = [(doc.to_dict().get('query'), doc.to_dict().get('response')) for doc in docs]
            return list(reversed(history))
        except Exception as e:
            logger.error(f"Error fetching history for {conversation_id}: {e}")
            return []

    def add_message(self, conversation_id: str, user_query: str, ai_response: str, user_id: str = None):
        """Add a new query-response pair and update conversation metadata."""
        if not self.db: # Fallback
            self._in_memory_fallback.setdefault(conversation_id, []).append((user_query, ai_response))
            self._in_memory_fallback[conversation_id] = self._in_memory_fallback[conversation_id][-MAX_CONVERSATION_HISTORY:]
            return

        try:
            # 1. Update the conversation metadata FIRST (ensure doc exists)
            conv_ref = self.db.collection('conversations').document(conversation_id)
            
            # Use a transaction-like approach or just set with merge
            # We fetch current state to avoid overwriting the title
            snapshot = conv_ref.get()
            meta = {
                'last_updated': firestore.SERVER_TIMESTAMP,
                'last_query': user_query[:50] + "..." if len(user_query) > 50 else user_query,
            }
            
            if user_id:
                meta['user_id'] = user_id
            
            if not snapshot.exists or 'title' not in snapshot.to_dict():
                meta['title'] = user_query[:40] + "..." if len(user_query) > 40 else user_query

            conv_ref.set(meta, merge=True)

            # 2. Store the specific message in the subcollection
            msg_doc_ref = conv_ref.collection('messages').document()
            msg_doc_ref.set({
                'query': user_query, 
                'response': ai_response, 
                'timestamp': firestore.SERVER_TIMESTAMP
            })

            logger.info(f"✅ Message saved to Firestore for conversation {conversation_id}")

        except Exception as e:
            logger.error(f"Error saving message to Firestore: {e}")

    def get_user_conversations(self, user_id: str) -> List[dict]:
        """Fetch list of conversation metadata for a specific user."""
        if not self.db or not user_id:
            return []

        try:
            # We remove order_by from the server-side query to avoid requiring 
            # a composite index (user_id + last_updated), which is a common failure point.
            # We limit to 50 and then sort in-memory.
            docs = self.db.collection('conversations') \
                .where('user_id', '==', user_id) \
                .limit(50) \
                .stream()

            conversations = []
            for doc in docs:
                data = doc.to_dict()
                conversations.append({
                    "id": doc.id,
                    "title": data.get('title', 'Untitled Consultation'),
                    "last_updated": data.get('last_updated')
                })

            # Sort in-memory instead (DESCENDING)
            conversations.sort(
                key=lambda x: (x['last_updated'].timestamp() if hasattr(x['last_updated'], 'timestamp') else 0), 
                reverse=True
            )

            return conversations[:20] # Return top 20
        except Exception as e:
            logger.error(f"Error fetching user conversations for {user_id}: {e}")
            return []