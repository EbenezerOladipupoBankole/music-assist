"""Test RAG query"""
from dotenv import load_dotenv
load_dotenv()

import asyncio
from rag_pipeline import RAGPipeline

async def test():
    pipeline = RAGPipeline()
    await pipeline.initialize()
    print(f"Vector store has {pipeline.vector_store.index.ntotal} vectors")
    
    result = await pipeline.query("What is the policy on ward choir auditions?")
    print("\n=== RESPONSE ===")
    print(result['answer'][:1000])
    print("\n=== SOURCES ===")
    print(result['sources'])

if __name__ == "__main__":
    asyncio.run(test())
