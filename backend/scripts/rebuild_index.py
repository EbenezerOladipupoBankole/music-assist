import asyncio
import os

from dotenv import load_dotenv

from rag_pipeline import RAGPipeline

# Load env vars
load_dotenv()

async def main():
    print("🧠 Starting Knowledge Base Rebuild...")
    
    # Initialize pipeline
    pipeline = RAGPipeline(
        vector_db_path="./data/vector_store",
        model_name=os.getenv("LLM_MODEL", "gpt-4o-mini")
    )
    
    # Needs to be initialized first to load basic stuff
    await pipeline.initialize()
    
    # Rebuild from the newly crawled 200+ docs
    print("📥 Processing documents from ./data/crawled...")
    result = await pipeline.rebuild_vector_store()
    
    print(f"✅ Success! Knowledge base now contains {result['documents_indexed']} documents.")

if __name__ == "__main__":
    asyncio.run(main())
