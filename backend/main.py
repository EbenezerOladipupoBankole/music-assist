"""
Music-Assist Backend API
FastAPI application with RAG pipeline for LDS music theory chatbot
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from datetime import datetime
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import sys
import re
import random

# Load environment variables from .env file
load_dotenv()

# Add root directory to path to import hymn_player
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Global variables for RAG components
rag_pipeline = None
hymn_player = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize RAG pipeline on startup"""
    global rag_pipeline, hymn_player
    
    from rag_pipeline import RAGPipeline
    from hymn_player import HymnPlayer
    
    # Initialize the RAG pipeline
    try:
        rag_pipeline = RAGPipeline(
            vector_db_path=os.getenv("VECTOR_DB_PATH", "./data/vector_store"),
            model_name=os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        )
        
        # Load or create vector store
        await rag_pipeline.initialize()
        
        print("✓ RAG Pipeline initialized successfully")
    except Exception as e:
        print(f"⚠ RAG Pipeline failed to initialize: {e}")
        rag_pipeline = None

    # Initialize Hymn Player
    try:
        hymn_player = HymnPlayer()
        print(f"✓ HymnPlayer initialized with {len(hymn_player.known_hymns)} hymns")
    except Exception as e:
        print(f"⚠ Could not initialize HymnPlayer: {e}")

    yield

# Initialize FastAPI app
app = FastAPI(
    title="Music-Assist API",
    description="RAG-powered chatbot for LDS music theory",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration for Firebase frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure with your Firebase domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    sources: List[dict]
    conversation_id: str
    timestamp: str

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0"
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0"
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """
    Main chat endpoint - processes user queries with RAG
    """
    try:
        # 1. Check for Hymn/Singing Request
        user_msg = message.message.lower().strip()
        
        # Look for "sing" or "play" followed by optional text
        sing_match = re.search(r'\b(sing|play)\b\s*(.*)', user_msg)
        
        # Relaxed check to include "yes", "ok", or if the keyword is early in the sentence
        is_request = (
            user_msg.startswith(("sing", "play", "can you", "could you", "please", "yes", "ok", "sure")) 
            or (sing_match and sing_match.start() < 10)
        )

        if hymn_player and sing_match and is_request:
            query = sing_match.group(2).strip()
            
            # 1. Try to find specific hymns first
            hymns = hymn_player.get_hymns(query)
            
            # 2. If no specific hymns found, check for generic request or empty query
            # We check for keywords that imply "pick one for me"
            is_generic = any(w in query.lower() for w in ["one", "any", "random", "something", "list", "song", "hymn"])
            
            if not hymns and (not query or is_generic):
                random_title = random.choice(hymn_player.known_hymns)
                hymns = hymn_player.get_hymns(random_title)
            
            if hymns:
                # Build HTML response for one or multiple hymns
                if len(hymns) == 1:
                    response_text = f"I can help with that! Here is the official recording for '{hymns[0]['title']}':<br><br><audio controls src=\"{hymns[0]['url']}\"></audio>"
                else:
                    response_text = "I found the following hymns for you:<br>"
                    for h in hymns:
                        response_text += f"<br><strong>{h['title']}</strong><br><audio controls src=\"{h['url']}\"></audio><br>"

                return ChatResponse(
                    response=response_text,
                    sources=[],
                    conversation_id=message.conversation_id or "sing_request",
                    timestamp=datetime.utcnow().isoformat(),
                )
            else:
                return ChatResponse(
                    response=f"I'm sorry, I couldn't find a hymn matching '{query}'. My current list of playable hymns includes: {', '.join(hymn_player.known_hymns)}.",
                    sources=[],
                    conversation_id=message.conversation_id or "sing_request_failed",
                    timestamp=datetime.utcnow().isoformat(),
                )

        # 2. Check for Greetings
        if user_msg in ["hello", "hi", "hey", "greetings"]:
            return ChatResponse(
                response="Hello! I am Music-Assist. I can help you with LDS music theory, find hymns, or answer questions about conducting. How can I help you today?",
                sources=[],
                conversation_id=message.conversation_id or "greeting",
                timestamp=datetime.utcnow().isoformat(),
            )

        if not rag_pipeline:
            raise HTTPException(status_code=503, detail="RAG pipeline not initialized")

        # Process the query through RAG pipeline
        result = await rag_pipeline.query(
            query=message.message,
            conversation_id=message.conversation_id,
            user_id=message.user_id
        )
        
        return ChatResponse(
            response=result["answer"],
            sources=result["sources"],
            conversation_id=result["conversation_id"],
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.post("/crawl/trigger")
async def trigger_crawl(admin_key: str):
    """
    Trigger web crawler to update document corpus
    Protected endpoint - requires admin key
    """
    if admin_key != os.getenv("ADMIN_KEY", ""):
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    try:
        from crawler import ChurchMusicCrawler
        
        crawler = ChurchMusicCrawler(
            output_dir="./data/crawled",
            rate_limit_delay=2.0
        )
        
        urls = [
            "https://www.churchofjesuschrist.org/media/music?lang=eng",
            "https://www.churchofjesuschrist.org/initiative/new-hymns?lang=eng",
            "https://www.churchofjesuschrist.org/callings/music/common-questions-about-music-in-church-meetings?lang=eng",
            "https://www.churchofjesuschrist.org/study/handbooks-and-callings/ward-or-branch-callings/music?lang=eng",
            "https://www.churchofjesuschrist.org/media/music/archived-content?lang=eng"
        ]
        
        results = await crawler.crawl_sites(urls)
        
        # Rebuild vector store with new data
        await rag_pipeline.rebuild_vector_store()
        
        return {
            "status": "success",
            "documents_crawled": results["total_documents"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crawl failed: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    try:
        if not rag_pipeline:
            raise HTTPException(status_code=503, detail="RAG pipeline not initialized")
        
        stats = await rag_pipeline.get_stats()
        
        return {
            "status": "success",
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )