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
import firebase_admin
from firebase_admin import credentials

# Add current directory to path to ensure local imports (like rag_pipeline) work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
load_dotenv()

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
        
        print("[OK] RAG Pipeline initialized successfully")
    except Exception as e:
        print(f"[WARNING] RAG Pipeline failed to initialize: {e}")
        rag_pipeline = None

    # Initialize Hymn Player
    try:
        hymn_player = HymnPlayer()
        print(f"[OK] HymnPlayer initialized with {len(hymn_player.known_hymns)} hymns")
    except Exception as e:
        print(f"[WARNING] Could not initialize HymnPlayer: {e}")

    # Initialize Firebase Admin
    try:
        if not firebase_admin._apps:
            firebase_json = os.getenv("FIREBASE_CONFIG_JSON")
            cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "./firebase-key.json")
            
            if firebase_json:
                import json
                cred_dict = json.loads(firebase_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                print("[OK] Firebase Admin initialized successfully (from Environment Variable)")
            elif os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                print(f"[OK] Firebase Admin initialized successfully (Local Key: {cred_path})")
            else:
                # Fallback to Application Default Credentials
                firebase_admin.initialize_app()
                print("[OK] Firebase Admin initialized successfully (ADC)")
    except Exception as e:
        print(f"[WARNING] Firebase Admin failed to initialize: {e}. Firebase features disabled.")

    yield

# Initialize FastAPI app
app = FastAPI(
    title="Music-Assist API",
    description="RAG-powered chatbot for LDS music theory",
    version="1.0.0",
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

class ChatResponse(BaseModel):
    response: str
    sources: List[dict]
    conversation_id: str
    timestamp: str
    confidence: Optional[str] = None
    search_method: Optional[str] = None

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
        
        # Look for "sing", "play", "listen to", "hear" followed by optional text
        sing_match = re.search(r'\b(sing|play|listen|hear)\b\s*(.*)', user_msg)
        
        # Liberal check for intent
        is_request = (
            user_msg.startswith(("sing", "play", "listen", "hear", "can you", "could you", "please", "yes", "ok", "sure")) 
            or (sing_match and sing_match.start() < 15)
        )

        if hymn_player and is_request and (sing_match or "hymn" in user_msg or "song" in user_msg):
            query = sing_match.group(2).strip() if sing_match else user_msg
            
            # Remove filler words
            query = re.sub(r'\b(me|to|a|the|hymn|song|number)\b', '', query).strip()
            
            # 1. Try to find specific hymns first
            hymns = hymn_player.get_hymns(query)
            
            # 2. If no specific hymns found, check for generic request
            is_generic = any(w in query.lower() for w in ["one", "any", "random", "something", "list", "song", "hymn"]) or not query
            
            if not hymns and is_generic:
                random_hymn = random.choice(hymn_player.hymns_db)
                hymns = [random_hymn]
            
            if hymns:
                if len(hymns) == 1:
                    h = hymns[0]
                    response_text = (
                        f"<div class='musical-response p-4 border-l-4 border-teal-500 bg-slate-50/50 rounded-r-xl mt-2 mb-4'>"
                        f"<div class='flex items-center gap-2 mb-2'>"
                        f"<svg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' class='text-teal-600'><path d='M9 18V5l12-2v13'></path><circle cx='6' cy='18' r='3'></circle><circle cx='18' cy='16' r='3'></circle></svg>"
                        f"<span class='text-xs font-black uppercase tracking-widest text-teal-700'>Now Performing</span>"
                        f"</div>"
                        f"<p class='font-serif text-lg mb-4 text-slate-900 italic'>\"{h['title']}\" — Hymn #{h['number']}</p>"
                        f"<audio controls class='w-full h-10 border-2 border-slate-100 rounded-lg shadow-sm' src=\"{h['url']}\"></audio>"
                        f"</div>"
                    )
                else:
                    response_text = "<div class='mb-4'><p class='mb-4'>I found multiple hymns matching your request. Which one would you like to hear?</p>"
                    for h in hymns:
                        response_text += (
                            f"<div class='mb-4 p-4 border border-slate-100 rounded-xl bg-slate-50/30'>"
                            f"<p class='font-serif font-bold text-slate-800 mb-2'>\"{h['title']}\" (#{h.get('number', '?')})</p>"
                            f"<audio controls class='w-full h-8' src=\"{h['url']}\"></audio>"
                            f"</div>"
                        )
                    response_text += "</div>"

                return ChatResponse(
                    response=response_text,
                    sources=[],
                    conversation_id=message.conversation_id or "sing_request",
                    timestamp=datetime.utcnow().isoformat(),
                )
            else:
                return ChatResponse(
                    response=f"I'm sorry, I couldn't find a hymn matching '{query}'. My current list of playable hymns includes: {', '.join(hymn_player.known_hymns[:10])}...",
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
            response=result["answer"] if result.get("answer") else "I found some relevant sources but couldn't generate a specific answer. Please check the sources below.",
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
    
    conversations = await asyncio.to_thread(
        rag_pipeline.memory.get_user_conversations, user_id
    )
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
    for i, (q, a) in enumerate(raw_history):
        formatted.append({
            "id": f"{conversation_id}_{i}_q",
            "sender": "user",
            "text": q,
            "timestamp": datetime.utcnow().isoformat() # Approx
        })
        formatted.append({
            "id": f"{conversation_id}_{i}_a",
            "sender": "ai",
            "text": a,
            "timestamp": datetime.utcnow().isoformat(),
            "sources": [] # Re-fetching sources is expensive, leaving empty for now
        })
    return formatted

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=int(os.getenv("PORT", 8080)),
        reload=True
    )