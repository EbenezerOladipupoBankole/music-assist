"""
Test script for Hybrid RAG System
Tests local data, web search, and off-topic detection
"""

import asyncio
import os
from dotenv import load_dotenv
from rag_pipeline import RAGPipeline

# Load environment variables
load_dotenv()


async def test_hybrid_rag():
    """Test the hybrid RAG system"""
    
    print("="*70)
    print("HYBRID RAG TEST SUITE")
    print("="*70)
    
    # Initialize RAG
    rag = RAGPipeline()
    await rag.initialize()
    
    # Test cases
    test_cases = [
        {
            "name": "Local Data Test - Should use ONLY local data",
            "query": "Can a youth be called as a music leader?",
            "expected": "local only"
        },
        {
            "name": "Web Search Test - Should trigger web search",
            "query": "Who is Mark Wilberg?",
            "expected": "hybrid (local + web)"
        },
        {
            "name": "Off-Topic Test - Should reject",
            "query": "What is the weather today?",
            "expected": "off-topic"
        },
        {
            "name": "Music Theory Test - Should use local data",
            "query": "What are the five principles of music?",
            "expected": "local only"
        }
    ]
    
    # Run tests
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}: {test['name']}")
        print(f"{'='*70}")
        print(f"Query: {test['query']}")
        print(f"Expected: {test['expected']}")
        print(f"-"*70)
        
        try:
            result = await rag.query(test['query'])
            
            print(f"\nSearch Method: {result['search_method']}")
            print(f"\nAnswer:\n{result['answer']}")
            
            if result['sources']:
                print(f"\nSources ({len(result['sources'])}):")
                for j, source in enumerate(result['sources'][:3], 1):
                    print(f"  {j}. [{source['type']}] {source.get('title', 'N/A')}")
            
            # Validate
            if test['expected'] in result['search_method']:
                print(f"\n[OK] Test PASSED - Used {result['search_method']}")
            else:
                print(f"\n[WARNING] Test result differs - Expected '{test['expected']}', got '{result['search_method']}'")
                
        except Exception as e:
            print(f"\n[ERROR] Test FAILED: {e}")
        
        print(f"\n{'='*70}\n")
    
    print("\nAll tests completed!")


if __name__ == "__main__":
    asyncio.run(test_hybrid_rag())
