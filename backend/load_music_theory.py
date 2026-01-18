"""
Load Music Theory Content into Vector Store
Adds educational content to existing crawled data
"""

import asyncio
import json
import os
from pathlib import Path
from rag_pipeline import RAGPipeline
from dotenv import load_dotenv

load_dotenv()


async def load_music_theory():
    """Load music theory JSON files into vector store"""
    
    print("="*70)
    print("LOADING MUSIC THEORY CONTENT")
    print("="*70)
    
    # Initialize RAG
    rag = RAGPipeline()
    await rag.initialize()
    
    # Path to music theory files
    theory_dir = Path("./data/music_theory")
    
    if not theory_dir.exists():
        print(f"[ERROR] Music theory directory not found: {theory_dir}")
        return
    
    # Load all JSON files
    theory_files = list(theory_dir.glob("*.json"))
    
    if not theory_files:
        print(f"[WARNING] No JSON files found in {theory_dir}")
        return
    
    print(f"\n[OK] Found {len(theory_files)} music theory files")
    
    documents = []
    
    for file_path in theory_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Create document with metadata
            doc = {
                "content": data.get("content", ""),
                "metadata": {
                    "title": data.get("title", file_path.stem),
                    "category": data.get("category", "Music Theory"),
                    "level": data.get("level", "Beginner"),
                    "source": str(file_path),
                    "type": "educational_content"
                }
            }
            
            documents.append(doc)
            print(f"[OK] Loaded: {data.get('title', file_path.name)}")
            
        except Exception as e:
            print(f"[ERROR] Failed to load {file_path.name}: {e}")
    
    # Add documents to RAG
    if documents:
        print(f"\n[INFO] Adding {len(documents)} documents to vector store...")
        await rag.add_documents(documents)
        print("[OK] Music theory content added successfully!")
        
        # Get stats
        stats = await rag.get_stats()
        print(f"\n[OK] Vector store now has {stats.get('total_documents', 'unknown')} total chunks")
    else:
        print("[WARNING] No documents to add")
    
    print("\n" + "="*70)
    print("COMPLETE")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(load_music_theory())
