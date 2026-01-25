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
            # 1. Store the message
            doc_ref = self.db.collection('conversations').document(conversation_id).collection('messages').document()
            doc_ref.set({
                'query': user_query, 
                'response': ai_response, 
                'timestamp': firestore.SERVER_TIMESTAMP
            })

            # 2. Update metadata for the sidebar
            conv_ref = self.db.collection('conversations').document(conversation_id)
            meta = {
                'last_updated': firestore.SERVER_TIMESTAMP,
                'last_query': user_query[:50] + "..." if len(user_query) > 50 else user_query
            }
            if user_id:
                meta['user_id'] = user_id
            
            # Use merge=True so we don't overwrite the initial title
            conv_ref.set(meta, merge=True)
            
            # Set title only if it doesn't exist (first message)
            snapshot = conv_ref.get()
            if not snapshot.exists or 'title' not in snapshot.to_dict():
                conv_ref.update({'title': user_query[:40] + "..." if len(user_query) > 40 else user_query})

        except Exception as e:
            logger.error(f"Error saving message to Firestore: {e}")

    def get_user_conversations(self, user_id: str) -> List[dict]:
        """Fetch list of conversation metadata for a specific user."""
        if not self.db or not user_id:
            return []

        try:
            docs = self.db.collection('conversations') \
                .where('user_id', '==', user_id) \
                .order_by('last_updated', direction=firestore.Query.DESCENDING) \
                .limit(20) \
                .stream()

            return [
                {
                    "id": doc.id,
                    "title": doc.to_dict().get('title', 'Untitled Consultation'),
                    "last_updated": doc.to_dict().get('last_updated')
                }
                for doc in docs
            ]
        except Exception as e:
            logger.error(f"Error fetching user conversations for {user_id}: {e}")
            return []