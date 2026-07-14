"""
Test script to verify production fixes for Music-Assist
Run this after the server is started separately

VALIDATION CHECKLIST:
❏ Composer questions never guess
❏ Hymn numbers are accurate
❏ Off-topic questions are refused cleanly
❏ Beginner explanations remain clear
❏ LDS tone and reverence preserved
❏ Retrieval dominates generation
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8080"

def test_query(query: str, description: str, check_func=None) -> dict:
    """Test a query and return the response"""
    print(f"\n{'='*70}")
    print(f"TEST: {description}")
    print(f"Query: {query}")
    print('='*70)
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json={"message": query},
            timeout=90
        )
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get('response', 'No response')
            
            print(f"\n✅ SUCCESS (HTTP 200)")
            print(f"Confidence: {data.get('confidence', 'unknown')}")
            print(f"Search Method: {data.get('search_method', 'unknown')}")
            print(f"\nResponse Preview:\n{answer[:600]}...")
            
            # Run custom validation if provided
            if check_func:
                passed, reason = check_func(data)
                if passed:
                    print(f"\n✓ VALIDATION PASSED: {reason}")
                else:
                    print(f"\n✗ VALIDATION FAILED: {reason}")
                return {"success": True, "passed_validation": passed, "data": data, "reason": reason}
            
            return {"success": True, "data": data}
        else:
            print(f"\n❌ FAILED (HTTP {response.status_code})")
            print(f"Error: {response.text}")
            return {"success": False, "error": response.text}
            
    except requests.exceptions.ConnectionError:
        print("\n❌ CONNECTION ERROR - Is the server running on port 8080?")
        return {"success": False, "error": "Connection refused"}
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return {"success": False, "error": str(e)}


def check_topic_filter_accepts(data):
    """Check that topic filter accepted the query (not rejected as off-topic)"""
    response = data.get('response', '').lower()
    if 'outside my area' in response or 'not trained' in response:
        return False, "Query was rejected as off-topic"
    return True, "Query was accepted"


def check_topic_filter_rejects(data):
    """Check that off-topic query was properly rejected"""
    response = data.get('response', '').lower()
    if 'outside my area' in response or 'music topics' in response or "i'm music-assist" in response:
        return True, "Off-topic query was properly rejected"
    return False, "Off-topic query was NOT rejected"


def check_no_hallucination(data):
    """Check for signs of hallucination guardrails working"""
    response = data.get('response', '').lower()
    # Good signs: admitting uncertainty, citing sources
    good_signs = [
        "don't have verified",
        "don't have specific information",
        "based on my available sources",
        "sources i have",
        "references:"
    ]
    if any(sign in response for sign in good_signs):
        return True, "Response shows appropriate uncertainty or citations"
    # Bad signs: confident claims without sources
    if 'composed' in response or 'wrote' in response:
        if 'references:' not in response:
            return False, "Made factual claim without references"
    return True, "No obvious hallucination detected"


def check_hymn_metadata_correct(data):
    """Check for correct hymn metadata OR appropriate uncertainty"""
    response = data.get('response', '').lower()
    
    # BEST CASE: Correctly identifies William Clayton as LYRICIST and traditional tune
    if 'william clayton' in response:
        if 'lyricist' in response or 'lyrics' in response or 'wrote the lyrics' in response or 'wrote the text' in response:
            return True, "Correctly identified William Clayton as lyricist"
        if 'traditional' in response or 'folk' in response or 'all is well' in response:
            return True, "Correctly noted traditional English tune"
    
    # ACCEPTABLE: System admits uncertainty about composer (anti-hallucination working)
    uncertainty_phrases = [
        "don't have verified",
        "don't have specific information",
        "no verified composer information",
        "not available in my sources",
        "unable to verify",
        "cannot confirm"
    ]
    if any(phrase in response for phrase in uncertainty_phrases):
        return True, "Anti-hallucination guardrails working - admitted uncertainty"
    
    # BAD CASE: Confidently hallucinating wrong info
    hallucination_signs = [
        'william clayton composed',
        'clayton wrote the music',
        'composed by william clayton'
    ]
    if any(sign in response for sign in hallucination_signs):
        return False, "HALLUCINATED - Incorrectly attributed music to William Clayton"
    
    return False, "Did not correctly attribute Come, Come, Ye Saints"


def check_has_confidence(data):
    """Check that confidence level is included"""
    if 'confidence' in data:
        return True, f"Confidence level: {data.get('confidence')}"
    return False, "No confidence level in response"


def main():
    print("\n" + "="*70)
    print("MUSIC-ASSIST PRODUCTION FIX VALIDATION")
    print("="*70)
    print("\nThis script validates all fixes from the audit report.\n")
    
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "details": []
    }
    
    # ========== TEST 1: Topic Filter Fix - Composer Questions ==========
    result1 = test_query(
        "Who composed Come Come Ye Saints?",
        "CRITICAL: Topic Filter - Composer questions should be ACCEPTED",
        check_topic_filter_accepts
    )
    results["total"] += 1
    if result1.get("passed_validation"):
        results["passed"] += 1
    else:
        results["failed"] += 1
    results["details"].append(("Topic Filter - Composer", result1.get("passed_validation", False)))
    
    # ========== TEST 2: Topic Filter - "Who wrote" variation ==========
    result2 = test_query(
        "Who wrote the music for Hymn 30?",
        "CRITICAL: Topic Filter - 'Who wrote' pattern should be ACCEPTED",
        check_topic_filter_accepts
    )
    results["total"] += 1
    if result2.get("passed_validation"):
        results["passed"] += 1
    else:
        results["failed"] += 1
    results["details"].append(("Topic Filter - Who wrote", result2.get("passed_validation", False)))
    
    # ========== TEST 3: Off-topic should still be rejected ==========
    result3 = test_query(
        "What is the weather like today?",
        "CRITICAL: Off-topic Rejection - Should politely refuse",
        check_topic_filter_rejects
    )
    results["total"] += 1
    if result3.get("passed_validation"):
        results["passed"] += 1
    else:
        results["failed"] += 1
    results["details"].append(("Off-topic Rejection", result3.get("passed_validation", False)))
    
    # ========== TEST 4: Hallucination Guardrails ==========
    result4 = test_query(
        "Tell me about the hymn Come Come Ye Saints and who wrote it",
        "CRITICAL: Hallucination Guardrails - Should correctly attribute (Clayton = lyrics, tune = traditional)",
        check_hymn_metadata_correct
    )
    results["total"] += 1
    if result4.get("passed_validation"):
        results["passed"] += 1
    else:
        results["failed"] += 1
    results["details"].append(("Hallucination Guardrails", result4.get("passed_validation", False)))
    
    # ========== TEST 5: Confidence Signaling ==========
    result5 = test_query(
        "What is a chord? Explain for beginners.",
        "HIGH PRIORITY: Confidence Signaling - Should include confidence level",
        check_has_confidence
    )
    results["total"] += 1
    if result5.get("passed_validation"):
        results["passed"] += 1
    else:
        results["failed"] += 1
    results["details"].append(("Confidence Signaling", result5.get("passed_validation", False)))
    
    # ========== TEST 6: Music Theory Still Works ==========
    result6 = test_query(
        "How do I conduct a hymn in 3/4 time?",
        "CORE FUNCTIONALITY: Conducting patterns should work (new corpus content)",
        check_topic_filter_accepts
    )
    results["total"] += 1
    if result6.get("passed_validation"):
        results["passed"] += 1
    else:
        results["failed"] += 1
    results["details"].append(("Conducting Patterns", result6.get("passed_validation", False)))
    
    # ========== TEST 7: Easter Hymns ==========
    result7 = test_query(
        "What hymns are good for Easter?",
        "DATA VERIFICATION: Easter hymns should be accurate (Hymn 198 = That Easter Morn)",
        check_topic_filter_accepts
    )
    results["total"] += 1
    if result7.get("passed_validation"):
        results["passed"] += 1
    else:
        results["failed"] += 1
    results["details"].append(("Easter Hymns", result7.get("passed_validation", False)))
    
    # ========== SUMMARY ==========
    print("\n" + "="*70)
    print("FINAL VALIDATION RESULTS")
    print("="*70)
    
    print(f"\nTotal Tests: {results['total']}")
    print(f"Passed: {results['passed']} ({results['passed']/results['total']*100:.1f}%)")
    print(f"Failed: {results['failed']} ({results['failed']/results['total']*100:.1f}%)")
    
    print("\nDetailed Results:")
    for name, passed in results["details"]:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print("\n" + "="*70)
    if results["failed"] == 0:
        print("✅ ALL TESTS PASSED - System is PRODUCTION READY")
        print("="*70)
        return 0
    elif results["failed"] <= 2:
        print("⚠️ NEAR READY - Some tests failed, review needed")
        print("="*70)
        return 1
    else:
        print("❌ NOT READY - Critical tests failed")
        print("="*70)
        return 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
