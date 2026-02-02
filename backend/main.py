"""
Music-Assist Backend API
FastAPI application with RAG pipeline for LDS music theory chatbot
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import json
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

# Using SQLite for memory and Local Disk for audio cache - No Cloud needed!

from rag_pipeline import RAGPipeline
from hymn_player import HymnPlayer
from audio_manager import AudioCacheManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_pipeline, hymn_player, audio_cache
    
    # 1. Init Local Audio Cache
    try:
        audio_cache = AudioCacheManager()
    except Exception as e:
        print(f"[ERROR] AudioCache failed: {e}")

    # 2. Init RAG (SQLite Memory inside)
    try:
        rag_pipeline = RAGPipeline(
            vector_db_path=os.getenv("VECTOR_DB_PATH", "./data/vector_store"),
            model_name=os.getenv("LLM_MODEL", "gpt-4o-mini")
        )
        await rag_pipeline.initialize()
        print("[OK] RAG & Memory Ready")
    except Exception as e:
        print(f"[ERROR] RAG initialization failed: {e}")

    # 3. Init Hymn Data
    try:
        hymn_player = HymnPlayer()
        print(f"[OK] HymnPlayer Ready")
    except Exception as e:
        print(f"[ERROR] HymnPlayer failed: {e}")

    yield

# Initialize FastAPI app
app = FastAPI(
    title="Music-Assist API",
    description="Offline-ready RAG chatbot for Church music",
    version="1.1.0",
    lifespan=lifespan
)



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

@app.get("/audio/hymn/{number}")
async def get_hymn_audio(number: int):
    """
    Retrieves hymn audio from LOCAL CACHE.
    Downloads once, serves many times. Faster and reliable.
    """
    if not (hymn_player and audio_cache):
        raise HTTPException(status_code=503, detail="Audio system not ready")
    
    # Find the hymn
    hymns = hymn_player.get_hymns(str(number))
    if not hymns:
        raise HTTPException(status_code=404, detail="Hymn not found")
    
    h = hymns[0]
    source_url = h['url']
    
    from fastapi.responses import FileResponse, StreamingResponse
    import requests

    # 1. Try to get from local disk
    try:
        local_path = await asyncio.to_thread(audio_cache.get_local_path, h['number'], source_url)
        if local_path and os.path.exists(local_path):
            logger.info(f"🔊 Serving Hymn {number} from Local Disk")
            return FileResponse(local_path, media_type="audio/mpeg")
    except Exception as e:
        logger.warning(f"Local cache failed for hymn {number}: {e}")

    # 2. Extreme Fallback: Proxy direct from source if disk fails
    try:
        def iterfile():
            with requests.get(source_url, stream=True, timeout=15) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=1024*1024):
                    yield chunk
        
        logger.info(f"🔄 Proxying Hymn {number} from official source (Disk Fallback)")
        return StreamingResponse(iterfile(), media_type="audio/mpeg")
    except Exception as e:
        logger.error(f"Audio proxy failed for Hymn {number}: {e}")
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
        "is_using_firestore": (getattr(rag_pipeline.memory, 'db', None) is not None) if (rag_pipeline and rag_pipeline.memory) else False
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

        # 1. Check for Hymn Audio Request (Typo resilient)
        sing_match = re.search(r'\b(sing|play|listen|hear|music for|plat|plsy)\b\s*(.*)', user_msg)
        has_audio_intent = any(w in user_msg for w in ["play", "sing", "listen", "audio", "recording", "plat", "plsy"])
        is_informational = any(w in user_msg for w in ["list", "about", "what is", "how many", "tell me", "explain"])

        if hymn_player and has_audio_intent and not is_informational:
            query = sing_match.group(2).strip() if sing_match else user_msg
            query = re.sub(r'\b(me|to|a|the|hymn|song|number)\b', '', query).strip()
            
            hymns = hymn_player.get_hymns(query)
            is_explicit_random = any(w in query.lower() for w in ["random", "something", "any song"])
            
            if not hymns and is_explicit_random:
                random_hymn = random.choice(hymn_player.hymns_db)
                hymns = [random_hymn]
            
                
            if hymns:
                primary_hymn = hymns[0]
                
                # Check if audio is available
                if primary_hymn.get('url') is None:
                    access_note = primary_hymn.get('access_note', 'Access hymn audio via Gospel Library app or ChurchofJesusChrist.org/music')
                    response_text = f"**{primary_hymn['title']}** (Hymn #{primary_hymn['number']})\n\n📱 **How to Listen:**\n{access_note}\n\n*Note: Direct audio playback is temporarily unavailable due to updates in the Church's media delivery system. The audio recordings are still available through the official Church apps and website.*"
                    
                    if rag_pipeline and rag_pipeline.memory:
                        await asyncio.to_thread(rag_pipeline.memory.add_message, cid, message.message, response_text, uid)

                    return ChatResponse(
                        response=response_text,
                        sources=[{
                            "type": "external",
                            "title": "Gospel Library App",
                            "url": "https://www.churchofjesuschrist.org/media/music"
                        }],
                        conversation_id=cid,
                        timestamp=datetime.utcnow().isoformat()
                    )
                else:
                    response_text = f"I've retrieved the official recording for **\"{primary_hymn['title']}\"** (Hymn #{primary_hymn['number']})."
                    
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
            # Extract first name if available
            name_part = ""
            if message.user_name:
                first_name = message.user_name.split()[0]  # Get first name only
                name_part = f" {first_name}"
            
            resp = f"Hi{name_part}! I am Music-Assist. How can I help you with Church music today?"
            
            # SAVE TO MEMORY
            if rag_pipeline and rag_pipeline.memory:
                await asyncio.to_thread(rag_pipeline.memory.add_message, cid, message.message, resp, uid)
                
            return ChatResponse(
                response=resp,
                sources=[],
                conversation_id=cid,
                timestamp=datetime.utcnow().isoformat(),
            )
        
        # 3. Check for "How are you" type questions
        how_are_you_patterns = ["how are you", "how are u", "how r you", "how r u", "how's it going", "how is it going", "what's up", "whats up"]
        if any(pattern in user_msg for pattern in how_are_you_patterns):
            name_part = ""
            if message.user_name:
                first_name = message.user_name.split()[0]
                name_part = f" {first_name}"
            
            resp = f"I'm doing well, thank you{name_part}! I'm here and ready to help you with Church music questions, hymn searches, conducting guidance, or music theory. What would you like to explore today?"
            
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

@app.post("/chat/stream")
async def chat_stream(message: ChatMessage):
    """
    Streaming chat endpoint for real-time AI responses.
    """
    if not rag_pipeline:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")

    from fastapi.responses import StreamingResponse
    
    cid = message.conversation_id
    uid = message.user_id
    user_msg = message.message.lower().strip()
    
    # 1. Check for audio intent in streaming too
    sing_match = re.search(r'\b(sing|play|listen|hear|music for|plat|plsy)\b\s*(.*)', user_msg)
    has_audio_intent = any(w in user_msg for w in ["play", "sing", "listen", "audio", "recording", "plat", "plsy"])
    is_informational = any(w in user_msg for w in ["list", "about", "what is", "how many", "tell me", "explain"])

    async def event_generator():
        if hymn_player and has_audio_intent and not is_informational:
            query = sing_match.group(2).strip() if sing_match else user_msg
            query = re.sub(r'\b(me|to|a|the|hymn|song|number)\b', '', query).strip()
            
            hymns = hymn_player.get_hymns(query)
            if not hymns and any(w in query.lower() for w in ["random", "something", "any song"]):
                hymns = [random.choice(hymn_player.hymns_db)]
            
            if hymns:
                h = hymns[0]
                final_cid = cid or f"conv_{int(datetime.utcnow().timestamp())}"
                
                # Check if audio URL exists
                if h.get('url') is None:
                    access_note = h.get('access_note', 'Access via Gospel Library app or ChurchofJesusChrist.org/music')
                    resp_text = f"**{h['title']}** (Hymn #{h['number']})\n\n📱 **How to Listen:**\n{access_note}\n\n*Note: Direct audio playback is temporarily unavailable due to updates in the Church's media delivery system.*"
                    
                    # Emit metadata without audio URL
                    meta_chunk = {
                        'type': 'metadata',
                        'conversation_id': final_cid,
                        'sources': [{
                            'type': 'external',
                            'title': 'Gospel Library App',
                            'url': 'https://www.churchofjesuschrist.org/media/music'
                        }]
                    }
                    yield json.dumps(meta_chunk) + "\n"
                    
                    # Emit result text
                    content_chunk = {'type': 'content', 'delta': resp_text}
                    yield json.dumps(content_chunk) + "\n"
                    
                    # Save to memory
                    if rag_pipeline and rag_pipeline.memory:
                        await asyncio.to_thread(rag_pipeline.memory.add_message, final_cid, message.message, resp_text, uid)
                    return
                else:
                    audio_title = f"{h['title']} (#{h['number']})"
                    resp_text = f"I've retrieved the official recording for **\"{h['title']}\"** (Hymn #{h['number']})."
                    
                    # Emit metadata chunk with audio info
                    meta_chunk = {
                        'type': 'metadata',
                        'audio_url': f"/audio/hymn/{h['number']}",
                        'audio_title': audio_title,
                        'conversation_id': final_cid
                    }
                    yield json.dumps(meta_chunk) + "\n"
                    
                    # Emit result text
                    content_chunk = {'type': 'content', 'delta': resp_text}
                    yield json.dumps(content_chunk) + "\n"
                    
                    # Save to memory
                    if rag_pipeline and rag_pipeline.memory:
                        await asyncio.to_thread(rag_pipeline.memory.add_message, final_cid, message.message, resp_text, uid)
                    return

        async for chunk in rag_pipeline.stream_query(message.message, cid, uid):
            yield f"{chunk}\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

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