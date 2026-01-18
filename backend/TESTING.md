# Testing Music-Assist RAG System

## Overview

Three test suites are available to validate the educational RAG system:

1. **Quick Demo** - 5 key questions (2 minutes)
2. **Educational Test** - 9 targeted test cases (5 minutes)
3. **Comprehensive User Test** - 65+ realistic questions (30+ minutes)

---

## Prerequisites

**Start the Server:**
```powershell
cd backend
python -m uvicorn main:app --port 8000
```

Wait for these messages:
```
[OK] RAG Pipeline initialized successfully
INFO: Uvicorn running on http://127.0.0.1:8000
```

---

## Test Suite 1: Quick Demo (Recommended First)

**Purpose:** Quickly verify the system is working

**Questions:**
- What is a chord?
- How do I read the treble clef?
- What key is Hymn 136 in?
- How do I transpose a hymn?
- Can a youth be called as a music leader?

**Run:**
```powershell
python quick_demo.py
```

**Expected:** Educational answers with examples from LDS hymns

---

## Test Suite 2: Educational Test

**Purpose:** Validate teaching capabilities

**Categories:**
- Music Theory Basics
- Reading Music  
- Hymn Application
- Practical Skills
- Hymn Analysis
- Church Policy
- Off-Topic Detection

**Run:**
```powershell
python test_educational_rag.py
```

**Expected:** Pass rate ≥ 75%

---

## Test Suite 3: Comprehensive User Test (Full Validation)

**Purpose:** Test with 65+ realistic user questions

**Categories (13 total):**

### Beginner Level
- Music Reading Basics (5 questions)
- Music Theory Concepts (5 questions)
- Piano and Organ (5 questions)
- Primary Music (5 questions)

### Intermediate Level
- Hymn Analysis (5 questions)
- Transposition (5 questions)
- Choir and Conducting (5 questions)
- Specific Hymn Help (5 questions)

### Advanced Level
- Advanced Music Theory (5 questions)
- Troubleshooting (5 questions)

### Support Categories
- Church Guidelines (5 questions)
- Resources (5 questions)
- Off-Topic Detection (5 questions)

**Run:**
```powershell
python comprehensive_user_test.py
```

**Duration:** 30-45 minutes  
**Output:** Detailed JSON results file

**Expected Results:**
- Success Rate: ≥ 90%
- Off-Topic Detection: 100%
- Beginner Questions: Clear, educational answers
- Policy Questions: Accurate with citations
- Avg Response Time: < 10 seconds

---

## Sample Questions by User Type

### **Absolute Beginner (New Pianist)**
- "What are the lines and spaces on a music staff?"
- "What does 4/4 time signature mean?"
- "How do I play hymns on the piano as a beginner?"

### **Ward Music Coordinator**
- "How do I choose appropriate sacrament hymns?"
- "What are the responsibilities of a music leader?"
- "Can a youth be called as a ward music coordinator?"

### **Choir Director**
- "What is SATB in choir music?"
- "How do I choose the right tempo for a hymn?"
- "How can I make congregational singing stronger?"

### **Organist**
- "What's the difference between playing piano and organ for church?"
- "How do I play the introduction to a hymn?"
- "Should I use the sustain pedal when playing hymns?"

### **Music Theory Student**
- "Explain chord progressions in LDS hymns"
- "What is modulation and when is it used in hymns?"
- "Explain the circle of fifths"

---

## Interpreting Results

### Success Metrics

**Quick Demo:**
- ✓ All 5 questions answered
- ✓ Educational explanations (not just definitions)
- ✓ Hymn examples included
- ✓ Response time < 10s

**Educational Test:**
- ✓✓✓ EXCELLENT: ≥ 7/9 pass (77%)
- ✓✓ GOOD: ≥ 5/9 pass (55%)
- ✓ FAIR: ≥ 3/9 pass (33%)

**Comprehensive Test:**
- ✓✓✓ EXCELLENT: ≥ 90% success
- ✓✓ GOOD: ≥ 75% success
- ✓ FAIR: ≥ 60% success

### Quality Indicators

**Good Educational Answer:**
- Defines concept clearly
- Uses simple language
- Gives concrete examples from hymns
- Includes practical application
- Cites sources
- Encouraging tone

**Poor Answer:**
- Just a definition with no explanation
- Uses jargon without defining it
- No hymn examples
- Too short (< 100 chars)
- Too long without structure (> 2000 chars)

---

## Troubleshooting

### "Connection Error"
**Problem:** Server not running  
**Solution:** Start server: `python -m uvicorn main:app --port 8000`

### "Timeout Error"
**Problem:** Question taking too long  
**Solution:** Check if web search is stuck, try again

### "Short/Poor Answers"
**Problem:** Not finding relevant content  
**Solution:** Check vector store loaded: Should show 3023 chunks

### "No Hymn Examples"
**Problem:** Not using music theory content  
**Solution:** Verify music theory files loaded:
```powershell
python load_music_theory.py
```

---

## Batch File Shortcuts (Windows)

**Start Server:**
```
start_server.bat
```

**Run Comprehensive Test:**
```
run_test.bat
```

---

## Expected Behavior Examples

### ✅ GOOD: Educational Answer
```
Q: What is a chord?

A: A chord is three or more notes played at the same time. Think of 
it like harmony voices singing together - each person sings a different 
note, but they blend to create a fuller sound.

For example, a C Major chord contains the notes C, E, and G. When you 
play these together, you hear a bright, stable, happy sound. You can 
hear this at the opening of "I Know That My Redeemer Lives" (Hymn 136).

Major chords (like C, F, G) have a bright quality, while minor chords 
(like A minor) sound more reflective or somber. Most LDS hymns use 
major chords extensively because they convey faith and joy.

(Source: Understanding Chords and Harmony)

References: Music Theory Fundamentals - Chords and Harmony
```

### ❌ BAD: Not Educational
```
Q: What is a chord?

A: A combination of three or more notes.
```

---

## Next Steps After Testing

1. **Review Failed Questions** - Check why they failed
2. **Adjust Content** - Add more specific content if needed
3. **Refine Prompts** - Improve educational approach
4. **Expand Coverage** - Add more hymn analyses
5. **Iterate** - Test again after improvements

---

## Contact & Support

If you encounter issues or want to improve the system:
1. Check vector store: Should have 3023 chunks
2. Verify music theory files exist in `data/music_theory/`
3. Review `rag_pipeline.py` prompt
4. Check server logs for errors

---

**Happy Testing! 🎵**
