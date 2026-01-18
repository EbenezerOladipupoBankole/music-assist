"""
Quick Demo - Test 5 Key Questions
Shows the educational RAG in action
"""

import requests
import time


def ask(question: str):
    """Ask a question and display the answer"""
    print(f"\n{'='*80}")
    print(f"Q: {question}")
    print(f"{'='*80}\n")
    
    try:
        response = requests.post(
            "http://127.0.0.1:8000/chat",
            json={"message": question},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(data['response'])
            print(f"\n[Method: {data.get('search_method', 'unknown')}]")
        else:
            print(f"ERROR: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to server. Is it running on port 8000?")
        print("\nTo start the server, run:")
        print("  cd backend")
        print("  python -m uvicorn main:app --port 8000")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    
    return True


def main():
    print("="*80)
    print("MUSIC-ASSIST RAG - QUICK DEMO")
    print("="*80)
    print("\nTesting 5 key questions that demonstrate the educational capabilities:\n")
    
    questions = [
        "What is a chord?",
        "How do I read the treble clef?",
        "What key is Hymn 136 'I Know That My Redeemer Lives' in?",
        "How do I transpose a hymn to a different key?",
        "Can a youth be called as a music leader?"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n\nQUESTION {i}/{len(questions)}")
        
        if not ask(question):
            print("\nTest stopped due to error.")
            break
        
        if i < len(questions):
            time.sleep(2)  # Brief pause between questions
    
    print(f"\n\n{'='*80}")
    print("DEMO COMPLETE")
    print("="*80)
    print("\nFor comprehensive testing, run: python comprehensive_user_test.py")
    print("="*80)


if __name__ == "__main__":
    main()
