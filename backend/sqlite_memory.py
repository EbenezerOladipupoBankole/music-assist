"""
SQLite-based Conversation Memory Module
Simple, fast, and requires no external services
"""

import os
import sqlite3
import logging
from typing import List, Tuple
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_CONVERSATION_HISTORY = 10

class SQLiteConversationMemory:
    """
    Manages conversation history using SQLite database.
    Simple, fast, and works offline.
    """
    def __init__(self, db_path: str = "./data/conversations.db"):
        self.db_path = db_path
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self._init_db()
        logger.info(f"✅ SQLite conversation memory initialized at: {self.db_path}")

    def _init_db(self):
        """Create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                title TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT,
                query TEXT,
                response TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        ''')
        
        # Create indexes for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_conv_user 
            ON conversations(user_id, last_updated DESC)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_msg_conv 
            ON messages(conversation_id, timestamp DESC)
        ''')
        
        conn.commit()
        conn.close()

    def get_history(self, conversation_id: str) -> List[Tuple[str, str]]:
        """Retrieve conversation history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT query, response FROM messages
                WHERE conversation_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (conversation_id, MAX_CONVERSATION_HISTORY))
            
            history = cursor.fetchall()
            conn.close()
            
            # Reverse to get chronological order
            return list(reversed(history))
        except Exception as e:
            logger.error(f"❌ Error fetching history for {conversation_id}: {e}")
            return []

    def add_message(self, conversation_id: str, user_query: str, ai_response: str, user_id: str = None):
        """Add a new query-response pair"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 1. Ensure conversation exists
            cursor.execute('''
                INSERT OR IGNORE INTO conversations (id, user_id, title, last_updated)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (conversation_id, user_id, user_query[:50]))
            
            # 2. Update last_updated and title if this is the first message
            cursor.execute('''
                UPDATE conversations 
                SET last_updated = CURRENT_TIMESTAMP,
                    title = CASE 
                        WHEN title IS NULL OR title = '' THEN ?
                        ELSE title
                    END
                WHERE id = ?
            ''', (user_query[:50], conversation_id))
            
            # 3. Add message
            cursor.execute('''
                INSERT INTO messages (conversation_id, query, response, timestamp)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (conversation_id, user_query, ai_response))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Saved message to conversation {conversation_id}")
        except Exception as e:
            logger.error(f"❌ Error saving message: {e}")

    def get_user_conversations(self, user_id: str) -> List[dict]:
        """Fetch list of conversations for a user"""
        if not user_id:
            return []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, title, last_updated 
                FROM conversations
                WHERE user_id = ?
                ORDER BY last_updated DESC
                LIMIT 20
            ''', (user_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            conversations = []
            for row in rows:
                conv_id, title, last_updated = row
                # Robust timestamp conversion
                try:
                    # SQLite CURRENT_TIMESTAMP is "YYYY-MM-DD HH:MM:SS"
                    # Add T and parse
                    clean_ts = last_updated.replace(" ", "T")
                    dt = datetime.fromisoformat(clean_ts)
                    ts_ms = int(dt.timestamp() * 1000)
                except Exception as e:
                    logger.warning(f"Timestamp parse error: {e} for {last_updated}")
                    ts_ms = 0
                
                conversations.append({
                    "id": conv_id,
                    "title": title or "Untitled Consultation",
                    "last_updated": ts_ms
                })
            
            logger.info(f"📊 Found {len(conversations)} conversations for user {user_id}")
            return conversations
        except Exception as e:
            logger.error(f"❌ Error fetching user conversations: {e}")
            return []
