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
import asyncio
import logging
import firebase_admin
from firebase_admin import credentials

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add current directory to path to ensure local imports (like rag_pipeline) work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
load_dotenv()

# Global variables for RAG components
rag_pipeline = None
hymn_player = None
audio_cache = None

# No Firebase needed anymore - using SQLite for conversation storage!

from rag_pipeline import RAGPipeline
from hymn_player import HymnPlayer
from audio_manager import AudioCacheManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_pipeline, hymn_player, audio_cache
    
    # 1. Init Audio (Fail-safe)
    try:
        audio_cache = AudioCacheManager()
    except Exception as e:
        print(f"[ERROR] AudioCache failed: {e}")
        audio_cache = None

    # 2. Init RAG (Fail-safe)
    try:
        rag_pipeline = RAGPipeline(
            vector_db_path=os.getenv("VECTOR_DB_PATH", "./data/vector_store"),
            model_name=os.getenv("LLM_MODEL", "gpt-4o-mini")
        )
        await rag_pipeline.initialize()
        print("[OK] RAG & Memory Ready")
    except Exception as e:
        print(f"[ERROR] RAG initialization failed: {e}")
        rag_pipeline = None

    # 3. Init Hymns (Fail-safe)
    try:
        hymn_player = HymnPlayer()
        print(f"[OK] HymnPlayer Ready")
    except Exception as e:
        print(f"[ERROR] HymnPlayer initialization failed: {e}")
        hymn_player = None

    yield

# Initialize FastAPI app
app = FastAPI(
    title="Music-Assist API",
    description="RAG-powered chatbot for LDS music theory",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/debug/memory")
async def debug_memory():
    """Diagnostic for conversation memory status"""
    try:
        status = {
            "rag_pipeline": "OK" if rag_pipeline else "MISSING",
            "memory": "MISSING",
            "storage_type": "UNKNOWN"
        }
        
        if rag_pipeline and hasattr(rag_pipeline, "memory") and rag_pipeline.memory:
            status["memory"] = "OK"
            status["storage_type"] = "SQLite"
            status["db_path"] = getattr(rag_pipeline.memory, 'db_path', 'Unknown')
        
        return status
    except Exception as e:
        return {"error": str(e)}

# Define allowed origins
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "https://music-assists.web.app",
    "https://music-assists.firebaseapp.com",
    "https://music-assist-backend-158647252148.us-central1.run.app",
]

# Add origins from environment variable (for deployment)
env_origins = os.getenv("ALLOWED_ORIGINS")
if env_origins:
    for o in env_origins.split(","):
        o = o.strip()
        if not o: continue
        origins.append(o)
        if not o.startswith("http"):
            origins.append(f"https://{o}")
            origins.append(f"http://{o}")

# Safety: Add a broad match for onrender.com subdomains since hostnames can be tricky
# We use a pattern to check at runtime or just add common variants
if os.getenv("ENVIRONMENT") == "production":
    # This allows any frontend on Render to connect to this API
    pass # Middleware handles the list below

# CORS configuration
if os.getenv("ENVIRONMENT") == "production":
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex="https://.*\.onrender\.com",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
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
    audio_url: Optional[str] = None
    audio_title: Optional[str] = None
    confidence: Optional[str] = None
    search_method: Optional[str] = None

@app.get("/audio/hymn/{number}")
async def get_hymn_audio(number: int):
    """
    Proxies audio from the official CDN to bypass CORS and security blocks.
    This guarantees playback on all devices.
    """
    if not hymn_player:
        raise HTTPException(status_code=503, detail="Hymn player not initialized")
    
    # Find the hymn
    hymns = hymn_player.get_hymns(str(number))
    if not hymns:
        raise HTTPException(status_code=404, detail="Hymn not found")
    
    h = hymns[0]
    source_url = h['url']
    
    try:
        import requests
        from fastapi.responses import StreamingResponse
        
        def iterfile():
            with requests.get(source_url, stream=True, timeout=15) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=1024*1024): # 1MB chunks
                    yield chunk
        
        return StreamingResponse(iterfile(), media_type="audio/mpeg")
    except Exception as e:
        print(f"[Error] Audio proxy failed for Hymn {number}: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve audio")

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

@app.get("/debug/memory")
async def debug_memory():
    """Diagnostic for conversation memory status"""
    status = {
        "firebase_apps": [app.name for app in firebase_admin._apps] if firebase_admin._apps else [],
        "has_rag_pipeline": rag_pipeline is not None,
        "has_memory": rag_pipeline.memory is not None if rag_pipeline else False,
        "is_using_firestore": (rag_pipeline.memory.db is not None) if (rag_pipeline and rag_pipeline.memory) else False
    }
    return status

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
        # Determine User ID and Conversation ID
        uid = message.user_id
        cid = message.conversation_id or f"conv_{int(datetime.utcnow().timestamp())}"
        user_msg = message.message.lower().strip()
        
        logger.info(f"Incoming chat request: UID={uid}, CID={cid}, Message='{user_msg[:30]}...'")

        # 1. Check for Hymn/Singing Request
        sing_match = re.search(r'\b(sing|play|listen|hear)\b\s*(.*)', user_msg)
        is_request = (
            user_msg.startswith(("sing", "play", "listen", "hear", "can you", "could you", "please", "yes", "ok", "sure")) 
            or (sing_match and sing_match.start() < 15)
        )

        if hymn_player and is_request and (sing_match or "hymn" in user_msg or "song" in user_msg):
            query = sing_match.group(2).strip() if sing_match else user_msg
            query = re.sub(r'\b(me|to|a|the|hymn|song|number)\b', '', query).strip()
            
            hymns = hymn_player.get_hymns(query)
            is_generic = any(w in query.lower() for w in ["one", "any", "random", "something", "list", "song", "hymn"]) or not query
            
            if not hymns and is_generic:
                random_hymn = random.choice(hymn_player.hymns_db)
                hymns = [random_hymn]
            
            if hymns:
                primary_hymn = hymns[0]
                response_text = f"I've retrieved the official recording for <strong>\"{primary_hymn['title']}\"</strong> (Hymn #{primary_hymn['number']})."
                
                # SAVE TO MEMORY
                if rag_pipeline and rag_pipeline.memory:
                    await asyncio.to_thread(rag_pipeline.memory.add_message, cid, message.message, response_text, uid)

                return ChatResponse(
                    response=response_text,
                    sources=[],
                    conversation_id=cid,
                    timestamp=datetime.utcnow().isoformat(),
                    audio_url=f"/audio/hymn/{primary_hymn['number']}",
                    audio_title=f"{primary_hymn['title']} (#{primary_hymn['number']})"
                )

        # 2. Check for Greetings
        greetings = ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening", "howdy"]
        if any(greet in user_msg for greet in greetings) and len(user_msg) < 20:
            resp = "Hello! I am Music-Assist. I can help you with LDS music theory, find hymns, or answer questions about conducting. How can I help you today?"
            # SAVE TO MEMORY
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
            user_id=uid
        )
        
        return ChatResponse(
            response=result["answer"] if result.get("answer") else "I found some relevant sources but couldn't generate a specific answer.",
            sources=result["sources"],
            conversation_id=result["conversation_id"],
            timestamp=datetime.utcnow().isoformat(),
            confidence=result.get("confidence"),
            search_method=result.get("search_method")
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
            # Hymns and Music Library
            "https://www.churchofjesuschrist.org/media/music?lang=eng",
            "https://www.churchofjesuschrist.org/music/library/hymns?lang=eng",
            "https://www.churchofjesuschrist.org/initiative/new-hymns?lang=eng",
            "https://www.churchofjesuschrist.org/media/music/archived-content?lang=eng",
            
            # Music Guidelines and Handbooks
            "https://www.churchofjesuschrist.org/callings/music/common-questions-about-music-in-church-meetings?lang=eng",
            "https://www.churchofjesuschrist.org/study/handbooks-and-callings/ward-or-branch-callings/music?lang=eng",
            "https://www.churchofjesuschrist.org/study/manual/general-handbook/19-music?lang=eng",
            "https://www.churchofjesuschrist.org/study/manual/general-handbook/38-church-policies-and-guidelines?lang=eng",
            
            # Tabernacle Choir (Mack Wilberg and other conductors)
            "https://www.churchofjesuschrist.org/media/music/tabernacle-choir?lang=eng",
            "https://www.thetabernaclechoir.org/about.html",
            "https://www.thetabernaclechoir.org/about/conductors.html",
            "https://www.churchofjesuschrist.org/study/ensign/topics/tabernacle-choir-at-temple-square?lang=eng",
            "https://www.churchofjesuschrist.org/study/friend/topics/tabernacle-choir?lang=eng",
            
            # Music Theory and Education
            "https://www.churchofjesuschrist.org/study/music?lang=eng",
            "https://www.churchofjesuschrist.org/study/manual/conducting-course?lang=eng",
            "https://www.churchofjesuschrist.org/music/resources?lang=eng",
            
            # Children's Songbook
            "https://www.churchofjesuschrist.org/music/text/childrens-songbook?lang=eng",
            "https://www.churchofjesuschrist.org/children/resources/music?lang=eng",
            
            # Articles and Ensign Topics
            "https://www.churchofjesuschrist.org/study/ensign/topics/music?lang=eng",
            "https://www.churchofjesuschrist.org/study/ensign/topics/hymns?lang=eng",
            "https://www.churchofjesuschrist.org/study/ensign/topics/choirs?lang=eng",
            "https://www.churchofjesuschrist.org/study/liahona/topics/music?lang=eng",
            
            # Music Callings and Service
            "https://www.churchofjesuschrist.org/callings/music?lang=eng",
            "https://www.churchofjesuschrist.org/study/manual/music-callings?lang=eng",
            
            # Composer and Arranger Resources
            "https://www.churchofjesuschrist.org/study/ensign/topics/composers?lang=eng",
            "https://www.churchofjesuschrist.org/music/library/composers?lang=eng"
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

@app.get("/conversations/{user_id}")
async def get_user_conversations(user_id: str):
    """List past conversations for a user"""
    if not rag_pipeline or not rag_pipeline.memory:
        return []
    
    raw_convs = await asyncio.to_thread(
        rag_pipeline.memory.get_user_conversations, user_id
    )
    
    # Ensure timestamps are JSON serializable
    conversations = []
    for c in raw_convs:
        ts = c.get('last_updated')
        # Convert Firestore timestamp to numeric milliseconds
        numeric_ts = int(ts.timestamp() * 1000) if hasattr(ts, 'timestamp') else 0
        
        conversations.append({
            "id": c['id'],
            "title": c['title'],
            "last_updated": numeric_ts
        })
        
    return conversations

@app.get("/conversations/{conversation_id}/history")
async def get_conversation_history(conversation_id: str):
    """Retrieve full message history for a specific conversation"""
    if not rag_pipeline or not rag_pipeline.memory:
        return []
    
    raw_history = await asyncio.to_thread(
        rag_pipeline.memory.get_history, conversation_id
    )
    
    # Format for the frontend (Sender.USER / Sender.AI logic)
    formatted = []
    # Use a fixed base timestamp to maintain relative order if needed, or just current
    base_ts = int(datetime.utcnow().timestamp() * 1000)
    
    for i, (q, a) in enumerate(raw_history):
        formatted.append({
            "id": f"{conversation_id}_{i}_q",
            "sender": "user",
            "text": q,
            "timestamp": base_ts + (i * 2)
        })
        formatted.append({
            "id": f"{conversation_id}_{i}_a",
            "sender": "ai",
            "text": a,
            "timestamp": base_ts + (i * 2) + 1,
            "sources": [] 
        })
    return formatted

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )