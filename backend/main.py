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

# Load environment variables from .env file
load_dotenv()

# Global variables for RAG components
rag_pipeline = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize RAG pipeline on startup"""
    global rag_pipeline
    
    from rag_pipeline import RAGPipeline
    
    # Initialize the RAG pipeline
    rag_pipeline = RAGPipeline(
        vector_db_path=os.getenv("VECTOR_DB_PATH", "./data/vector_store"),
        model_name=os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    )
    
    # Load or create vector store
    await rag_pipeline.initialize()
    
    print("✓ RAG Pipeline initialized successfully")
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