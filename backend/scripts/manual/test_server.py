"""
Test script to verify backend server is running and responding
"""
import requests
import json

def test_server():
    base_url = "http://localhost:8000"
    
    print("="*70)
    print("🧪 TESTING MUSIC-ASSIST BACKEND SERVER")
    print("="*70)
    
    # Test 1: Health Check
    print("\n[TEST 1] Health Check...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        assert response.status_code == 200
        print("✅ Health check PASSED")
    except Exception as e:
        print(f"❌ Health check FAILED: {e}")
        return False
    
    # Test 2: RAG Chat
    print("\n[TEST 2] RAG Chat Query...")
    try:
        test_message = "What is a chord?"
        payload = {
            "message": test_message,
            "conversation_id": "test_001"
        }
        
        response = requests.post(f"{base_url}/chat", json=payload)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nQuery: {test_message}")
            print(f"\nResponse: {data['response'][:200]}...")
            print(f"\nSources: {len(data.get('sources', []))} documents")
            print("✅ RAG chat PASSED")
        else:
            print(f"❌ RAG chat FAILED with status {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ RAG chat FAILED: {e}")
        return False
    
    # Test 3: Stats Endpoint
    print("\n[TEST 3] Stats Endpoint...")
    try:
        response = requests.get(f"{base_url}/stats")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            stats = data.get('statistics', {})
            print(f"Total Queries: {stats.get('total_queries', 0)}")
            print(f"Total Cost: ${stats.get('total_cost', 0):.4f}")
            print("✅ Stats endpoint PASSED")
        else:
            print(f"⚠️ Stats endpoint returned status {response.status_code}")
            
    except Exception as e:
        print(f"⚠️ Stats endpoint error: {e}")
    
    print("\n" + "="*70)
    print("🎉 ALL CRITICAL TESTS PASSED!")
    print("="*70)
    return True

if __name__ == "__main__":
    test_server()
