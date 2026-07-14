"""
Comprehensive User Question Test Suite
Tests the RAG with realistic questions users would ask based on project goals
"""

import requests
import time
import json
from datetime import datetime


def ask_question(question: str, category: str = "") -> dict:
    """Send question to RAG and get response"""
    url = "http://127.0.0.1:8080/chat"
    
    try:
        print(f"\n{'='*80}")
        if category:
            print(f"CATEGORY: {category}")
        print(f"{'='*80}")
        print(f"Q: {question}")
        print(f"-"*80)
        
        start_time = time.time()
        response = requests.post(url, json={"message": question}, timeout=60)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            answer = data['response']
            
            print(f"\nA: {answer}\n")
            print(f"[Response Time: {response_time:.2f}s | Method: {data.get('search_method', 'unknown')}]")
            
            return {
                "success": True,
                "question": question,
                "answer": answer,
                "response_time": response_time,
                "search_method": data.get('search_method', 'unknown'),
                "answer_length": len(answer)
            }
        else:
            print(f"\n[ERROR] HTTP {response.status_code}")
            return {"success": False, "question": question, "error": f"HTTP {response.status_code}"}
            
    except requests.exceptions.ConnectionError:
        print("\n[ERROR] Cannot connect to server on port 8080")
        return {"success": False, "question": question, "error": "Connection failed"}
    except Exception as e:
        print(f"\n[ERROR] {e}")
        return {"success": False, "question": question, "error": str(e)}


def main():
    """Test with comprehensive user questions"""
    
    print("="*80)
    print("COMPREHENSIVE USER QUESTION TEST")
    print(f"Testing Music-Assist RAG with realistic user questions")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Realistic questions organized by user type and scenario
    test_questions = [
        # ============ ABSOLUTE BEGINNERS ============
        {
            "category": "BEGINNER - Music Reading Basics",
            "questions": [
                "What are the lines and spaces on a music staff?",
                "How do I read notes on the treble clef?",
                "What do the sharps and flats at the beginning mean?",
                "What does 4/4 time signature mean?",
                "What is the difference between whole notes and half notes?",
            ]
        },
        
        # ============ MUSIC THEORY FUNDAMENTALS ============
        {
            "category": "BEGINNER - Music Theory Concepts",
            "questions": [
                "What is a chord?",
                "Explain major and minor chords",
                "What is a scale?",
                "What does 'key' mean in music?",
                "What's the difference between melody and harmony?",
            ]
        },
        
        # ============ HYMN-SPECIFIC QUESTIONS ============
        {
            "category": "INTERMEDIATE - Hymn Analysis",
            "questions": [
                "What key is 'I Know That My Redeemer Lives' in?",
                "Analyze the time signature of 'I Need Thee Every Hour'",
                "What makes 'The Spirit of God' sound so powerful?",
                "Why is 'Come, Come, Ye Saints' in 4/4 time?",
                "What's the vocal range of 'I Stand All Amazed'?",
            ]
        },
        
        # ============ PIANO/ORGAN PLAYING ============
        {
            "category": "PRACTICAL - Piano and Organ",
            "questions": [
                "How do I play hymns on the piano as a beginner?",
                "What's the easiest way to accompany congregational singing?",
                "Should I use the sustain pedal when playing hymns?",
                "What's the difference between playing piano and organ for church?",
                "How do I play the introduction to a hymn?",
            ]
        },
        
        # ============ TRANSPOSITION ============
        {
            "category": "INTERMEDIATE - Transposition",
            "questions": [
                "How do I transpose a hymn to a different key?",
                "This hymn is too high for our congregation. What should I do?",
                "Can you explain how to transpose from F to G?",
                "What's the easiest key for congregational singing?",
                "How do I know if a key is too high or too low?",
            ]
        },
        
        # ============ CHOIR DIRECTING ============
        {
            "category": "INTERMEDIATE - Choir and Conducting",
            "questions": [
                "How do I choose the right tempo for a hymn?",
                "What is SATB in choir music?",
                "How do I help my choir blend better?",
                "What does 'soprano' mean in hymn singing?",
                "How can I make congregational singing stronger?",
            ]
        },
        
        # ============ CHURCH MUSIC POLICY ============
        {
            "category": "POLICY - Church Guidelines",
            "questions": [
                "Can a youth be called as a ward music coordinator?",
                "What are the responsibilities of a music leader?",
                "How do I choose appropriate sacrament hymns?",
                "Who can serve in music callings?",
                "What does the handbook say about church music?",
            ]
        },
        
        # ============ SPECIFIC HYMN HELP ============
        {
            "category": "PRACTICAL - Specific Hymn Help",
            "questions": [
                "What hymns are good for sacrament meeting?",
                "How do I play Hymn 2 'The Spirit of God'?",
                "What's a good opening hymn for testimony meeting?",
                "Are there hymns in 3/4 time that are easy to play?",
                "Which hymns are best for funerals?",
            ]
        },
        
        # ============ ADVANCED MUSIC THEORY ============
        {
            "category": "ADVANCED - Music Theory",
            "questions": [
                "Explain chord progressions in LDS hymns",
                "What is a dominant seventh chord?",
                "How do I identify intervals in music?",
                "What is modulation and when is it used in hymns?",
                "Explain the circle of fifths",
            ]
        },
        
        # ============ TROUBLESHOOTING ============
        {
            "category": "PRACTICAL - Problems and Solutions",
            "questions": [
                "I keep making mistakes when I play hymns. What should I do?",
                "The congregation isn't singing loudly. How can I help?",
                "How do I practice hymns effectively?",
                "What if I don't know all the notes in a hymn?",
                "How can I play hymns more smoothly?",
            ]
        },
        
        # ============ PRIMARY MUSIC ============
        {
            "category": "PRIMARY - Children's Songs",
            "questions": [
                "How do I teach children to sing a new song?",
                "What's the best way to teach 'I Am a Child of God'?",
                "How do I help children learn rhythm?",
                "What are some fun ways to teach Primary songs?",
                "How do I choose songs for Primary?",
            ]
        },
        
        # ============ MUSIC EQUIPMENT/RESOURCES ============
        {
            "category": "RESOURCES - Tools and Materials",
            "questions": [
                "Where can I find LDS hymn sheet music?",
                "What's the Sacred Music app?",
                "How can I access hymn recordings?",
                "Are there resources for learning to play the organ?",
                "Where can I find simplified hymn arrangements?",
            ]
        },
        
        # ============ OFF-TOPIC (Should be Rejected) ============
        {
            "category": "OFF-TOPIC - Should Reject",
            "questions": [
                "What's the weather like today?",
                "How do I bake a cake?",
                "Tell me about the stock market",
                "What's the latest news?",
                "Who won the football game?",
            ]
        },
    ]
    
    # Run all tests
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_questions": 0,
        "successful": 0,
        "failed": 0,
        "categories": {},
        "details": []
    }
    
    for category_group in test_questions:
        category = category_group["category"]
        questions = category_group["questions"]
        
        category_results = {
            "total": len(questions),
            "successful": 0,
            "failed": 0,
            "avg_response_time": 0,
            "questions": []
        }
        
        print(f"\n\n{'#'*80}")
        print(f"# {category}")
        print(f"# Testing {len(questions)} questions")
        print(f"{'#'*80}")
        
        for question in questions:
            result = ask_question(question, category)
            
            results["total_questions"] += 1
            
            if result["success"]:
                results["successful"] += 1
                category_results["successful"] += 1
                category_results["avg_response_time"] += result.get("response_time", 0)
            else:
                results["failed"] += 1
                category_results["failed"] += 1
            
            category_results["questions"].append(result)
            results["details"].append(result)
            
            # Small delay between questions
            time.sleep(1)
        
        # Calculate average response time
        if category_results["successful"] > 0:
            category_results["avg_response_time"] /= category_results["successful"]
        
        results["categories"][category] = category_results
    
    # Print summary
    print(f"\n\n{'='*80}")
    print("FINAL SUMMARY")
    print(f"{'='*80}")
    print(f"\nTotal Questions: {results['total_questions']}")
    print(f"Successful: {results['successful']} ({results['successful']/results['total_questions']*100:.1f}%)")
    print(f"Failed: {results['failed']} ({results['failed']/results['total_questions']*100:.1f}%)")
    
    print(f"\n{'-'*80}")
    print("CATEGORY BREAKDOWN")
    print(f"{'-'*80}")
    
    for category, stats in results["categories"].items():
        success_rate = stats['successful'] / stats['total'] * 100 if stats['total'] > 0 else 0
        print(f"\n{category}:")
        print(f"  Success: {stats['successful']}/{stats['total']} ({success_rate:.1f}%)")
        if stats['successful'] > 0:
            print(f"  Avg Response Time: {stats['avg_response_time']:.2f}s")
    
    # Save results
    output_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'-'*80}")
    print(f"Detailed results saved to: {output_file}")
    print(f"{'='*80}\n")
    
    # Assessment
    print("\nASSESSMENT:")
    if results['successful'] >= results['total_questions'] * 0.9:
        print("✓✓✓ EXCELLENT: RAG is performing at a high level!")
    elif results['successful'] >= results['total_questions'] * 0.75:
        print("✓✓ GOOD: RAG is working well with room for improvement")
    elif results['successful'] >= results['total_questions'] * 0.5:
        print("✓ FAIR: RAG is functional but needs work")
    else:
        print("✗ NEEDS ATTENTION: Significant issues detected")
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
