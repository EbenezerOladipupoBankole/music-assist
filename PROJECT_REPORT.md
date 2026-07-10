# Music-Assist: Project Technical Report

## 1. Problem Approach
The **Music-Assist** project was designed to solve the fragmentation of official music resources within the LDS Church ecosystem. Guidelines, hymn history, and audio recordings are currently spread across multiple platforms (General Handbook, Sacred Music Library, and various PDF manuals). 

Our approach was built on **Reliability and Authority**:
*   **Source Truth:** We prioritized official Handbook sections (19.4.3.3, 19.3.7.1) as the primary knowledge base.
*   **Technical Stability:** We moved from external cloud dependencies to a "Local-First" architecture to ensure that network fluctuations or API key issues wouldn't break the user experience.
*   **Concise Intelligence:** We engineered the system to differentiate between "Quick Lookups" (Hymn titles/numbers) and "Complex Inquiries" (Policy advice), providing tailored response lengths for each.

## 2. System Architecture
The application follows a modern, decoupled Full-Stack architecture:

### **Frontend (The Interface)**
*   **Tech:** React 18, Vite, TypeScript.
*   **Styling:** Vanilla CSS & Tailwind CSS for a premium "Glassmorphism" design.
*   **State Management:** Local React state with persistent conversation tracking via the backend.

### **Backend (The Engine)**
*   **Framework:** FastAPI (Python 3.10+).
*   **AI Orchestration:** LangChain for RAG pipeline management.
*   **Vector Database:** FAISS (Facebook AI Similarity Search) storing 437+ high-dimensional embeddings.
*   **LLM:** OpenAI GPT-4o-mini (chosen for its balance of speed and reasoning).

### **Storage Layer**
*   **Conversation Memory:** Local SQLite database for low-latency message history.
*   **Knowledge Base:** Multi-directory JSON strategy (Crawled content + Structured Hymn Metadata).
*   **Audio Assets:** Local Disk Cache manager that proxies and saves MP3 files to bypass CORS and CDN blocks.

## 3. Design Decisions
*   **Decision: RAG (Retrieval-Augmented Generation) vs. Fine-tuning**
    *   *Reasoning:* RAG allowed us to keep the data 100% accurate and up-to-date. Fine-tuning would lose precision on specific hymn numbers and would be expensive to update as new hymns are released in 2024/2025.
*   **Decision: Local Persistence over Cloud (Firebase)**
    *   *Reasoning:* We migrated away from Firebase to SQLite/Local Storage to eliminate "Cold Starts" and credential management overhead, making the system "Portable" and significantly faster for researchers.
*   **Decision: Hybrid Metadata Extraction**
    *   *Reasoning:* Standard semantic search often fails with numbers (e.g., searching "193" might return similar lyrics instead of the specific hymn number). We implemented a regex-based metadata extractor that forces the RAG pipeline to prioritize exact numerical matches.

## 4. Evaluation, Testing, and Deployment
### **Evaluation**
*   **Confidence Scoring:** The pipeline calculates a "Confidence Level" (High/Medium/Low) based on the proximity of documents found.
*   **Intent Filtering:** We implemented a rigorous music-specific query filter to prevent the bot from answering off-topic questions, preserving its status as an "Ecclesiastical AI."

### **Testing**
*   **Edge Case Verification:** We tested with controversial policy questions (e.g., "Auditions for choirs" or "Brass instruments in the chapel") to ensure citations always pointed to the correct Handbook subsection.
*   **Link Verification:** After encountering 404 errors with official CDN links, we implemented a multi-source fallback strategy and a local caching mechanism.

### **Deployment**
*   **Git Policy:** Large binary files (Vector Store datasets) are managed via `.gitignore` to maintain a lean repository.
*   **Modular Scripts:** Created dedicated maintenance scripts (`rebuild_index.py`, `run_deep_crawl.py`) for easy system updates in production environments.

---
*Created by Ebenezer Bankole 
