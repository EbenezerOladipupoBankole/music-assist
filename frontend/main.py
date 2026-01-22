import os
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict

# Assume rag_pipeline is in the same directory
from rag_pipeline import RAGPipeline

# --- App Initialization ---
app = FastAPI(
    title="Music-Assist API",
    description="Backend for Music-Assist RAG application",
    version="1.0.0"
)

rag_pipeline = RAGPipeline(vector_db_path="./data/vector_store")

@app.on_event("startup")
async def startup_event():
    """Initializes the RAG pipeline on application startup."""
    print("INFO:    Starting RAG pipeline initialization...")
    if not os.getenv("OPENAI_API_KEY"):
        print("CRITICAL: OPENAI_API_KEY environment variable not set.")
    await rag_pipeline.initialize()
    if rag_pipeline.vector_store:
        print(f"INFO:    RAG pipeline initialized successfully with {rag_pipeline.vector_store.index.ntotal} documents.")
    else:
        print("WARNING: RAG pipeline started but vector store is NOT available.")

# Configure CORS
# TODO: Replace with your actual Firebase Hosting URL in production
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://your-music-assist-app.web.app",
    "https://your-music-assist-app.firebaseapp.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Models ---
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None

class Source(BaseModel):
    type: str
    title: str
    source: str
    url: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict]
    conversation_id: str

# --- API Endpoints ---
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Receives a user message and returns the RAG pipeline response."""
    if not rag_pipeline.qa_chain:
        raise HTTPException(
            status_code=503, 
            detail="Service Unavailable: The knowledge base is not initialized. Please try again later."
        )
    
    try:
        result = await rag_pipeline.query(
            query=request.message,
            conversation_id=request.conversation_id,
            user_id=request.user_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}")
    except Exception as e:
        print(f"ERROR:   Error during query processing: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred while processing your request.")