"""
Simple Terminal Chat Client for Hybrid RAG Testing
"""

import requests
import json


def chat():
    """Interactive chat client"""
    print("="*70)
    print("HYBRID RAG MUSIC-ASSIST CHAT")
    print("="*70)
    print("\nTest Cases:")
    print("1. Local Data: 'Can a youth be called as a music leader?'")
    print("2. Web Search: 'Who is Mark Wilberg?'")
    print("3. Off-Topic: 'What is the weather today?'")
    print("\nType 'quit' to exit")
    print("="*70)
    
    url = "http://127.0.0.1:8000/chat"
    
    while True:
        print("\n" + "-"*70)
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\nGoodbye!")
            break
        
        if not user_input:
            continue
        
        try:
            # Send request
            response = requests.post(url, json={"message": user_input})
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"\n[Search Method: {data.get('search_method', 'unknown')}]")
                print(f"\nAssistant:\n{data['response']}")
                
                if data.get('sources'):
                    print(f"\n[{len(data['sources'])} sources used]")
                    
            else:
                print(f"\nError: {response.status_code}")
                print(response.text)
                
        except requests.exceptions.ConnectionError:
            print("\n[ERROR] Cannot connect to server. Is it running on port 8000?")
        except Exception as e:
            print(f"\n[ERROR] {e}")


if __name__ == "__main__":
    chat()
