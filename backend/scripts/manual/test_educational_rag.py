"""
Test Suite for Educational Music Theory RAG
Tests if the system can teach music concepts to beginners
"""

import requests
import json
from typing import Dict

def test_question(question: str, expected_keywords: list) -> Dict:
    """
    Test a question and check if response contains expected educational elements
    """
    url = "http://127.0.0.1:8000/chat"
    
    try:
        response = requests.post(url, json={"message": question}, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            answer = data['response']
            
            # Check if answer contains expected keywords
            found_keywords = [kw for kw in expected_keywords if kw.lower() in answer.lower()]
            missing_keywords = [kw for kw in expected_keywords if kw.lower() not in answer.lower()]
            
            return {
                "success": True,
                "answer": answer,
                "found_keywords": found_keywords,
                "missing_keywords": missing_keywords,
                "search_method": data.get('search_method', 'unknown'),
                "length": len(answer)
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}"
            }
    
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "Cannot connect to server. Is it running on port 8000?"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def main():
    """Run comprehensive test suite"""
    
    print("="*80)
    print("EDUCATIONAL MUSIC THEORY RAG - TEST SUITE")
    print("="*80)
    print("\nTesting if the RAG can TEACH music theory to beginners...\n")
    
    # Test cases: (question, expected keywords/concepts)
    test_cases = [
        {
            "category": "Music Theory Basics",
            "question": "What is a chord?",
            "expected": ["three", "notes", "together", "example"],
            "goal": "Should TEACH the concept, not just define"
        },
        {
            "category": "Reading Music",
            "question": "How do I read the treble clef?",
            "expected": ["lines", "spaces", "EGBDF", "FACE", "staff"],
            "goal": "Should explain staff notation for beginners"
        },
        {
            "category": "Hymn Application",
            "question": "Explain the time signature in hymns",
            "expected": ["4/4", "3/4", "beats", "measure", "common time"],
            "goal": "Should teach time signatures with hymn examples"
        },
        {
            "category": "Practical Skills",
            "question": "How do I transpose a hymn to a different key?",
            "expected": ["scale", "interval", "step", "example", "method"],
            "goal": "Should give step-by-step instructions"
        },
        {
            "category": "Hymn Analysis",
            "question": "What key is 'I Know That My Redeemer Lives' in?",
            "expected": ["B♭", "flat", "major", "Hymn 136"],
            "goal": "Should identify key and explain"
        },
        {
            "category": "Music Theory Concept",
            "question": "What's the difference between major and minor chords?",
            "expected": ["bright", "happy", "sad", "reflective", "sound", "third"],
            "goal": "Should explain the emotional difference"
        },
        {
            "category": "Beginner Piano",
            "question": "How do I play hymns on piano?",
            "expected": ["right hand", "left hand", "melody", "chord", "practice"],
            "goal": "Should give practical beginner advice"
        },
        {
            "category": "Church Policy (Still Works)",
            "question": "Can a youth be called as a music leader?",
            "expected": ["yes", "youth", "calling", "handbook"],
            "goal": "Should still answer policy questions"
        },
        {
            "category": "Off-Topic Detection",
            "question": "What's the weather like today?",
            "expected": ["not trained", "music", "church"],
            "goal": "Should reject off-topic questions"
        }
    ]
    
    results = {
        "passed": 0,
        "failed": 0,
        "details": []
    }
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}/{len(test_cases)}: {test['category']}")
        print(f"{'='*80}")
        print(f"Question: {test['question']}")
        print(f"Goal: {test['goal']}")
        print(f"-"*80)
        
        result = test_question(test['question'], test['expected'])
        
        if not result['success']:
            print(f"\n[FAILED] {result['error']}")
            results['failed'] += 1
            continue
        
        print(f"\nSearch Method: {result['search_method']}")
        print(f"Answer Length: {result['length']} characters")
        print(f"\nAnswer:\n{result['answer'][:500]}...")  # Show first 500 chars
        
        # Evaluate quality
        found_ratio = len(result['found_keywords']) / len(test['expected'])
        
        print(f"\n[EVALUATION]")
        print(f"Expected Keywords Found: {len(result['found_keywords'])}/{len(test['expected'])}")
        print(f"✓ Found: {', '.join(result['found_keywords'])}")
        if result['missing_keywords']:
            print(f"✗ Missing: {', '.join(result['missing_keywords'])}")
        
        # Determine pass/fail
        if found_ratio >= 0.5:  # At least 50% of keywords found
            print(f"\n[PASS] ✓ Answer appears educational and relevant")
            results['passed'] += 1
            test_result = "PASS"
        else:
            print(f"\n[FAIL] ✗ Answer missing key educational elements")
            results['failed'] += 1
            test_result = "FAIL"
        
        results['details'].append({
            "category": test['category'],
            "question": test['question'],
            "result": test_result,
            "found_ratio": found_ratio,
            "answer_length": result['length']
        })
    
    # Summary
    print(f"\n\n{'='*80}")
    print("FINAL RESULTS")
    print(f"{'='*80}")
    print(f"\nTotal Tests: {len(test_cases)}")
    print(f"Passed: {results['passed']} ({results['passed']/len(test_cases)*100:.1f}%)")
    print(f"Failed: {results['failed']} ({results['failed']/len(test_cases)*100:.1f}%)")
    
    print(f"\n{'='*80}")
    print("ASSESSMENT")
    print(f"{'='*80}")
    
    if results['passed'] >= 7:  # 7/9 = 77%
        print("\n✓✓✓ EXCELLENT: RAG is functioning as an educational tool!")
        print("The system successfully teaches music theory concepts.")
    elif results['passed'] >= 5:  # 5/9 = 55%
        print("\n✓✓ GOOD: RAG has educational capability but needs improvement.")
        print("Review failed tests and adjust prompts/content.")
    else:
        print("\n✗ NEEDS WORK: RAG not yet meeting educational goals.")
        print("Significant improvements needed in content or prompts.")
    
    # Save results
    with open('test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to test_results.json")


if __name__ == "__main__":
    main()
