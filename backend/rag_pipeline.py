"""
RAG Pipeline for Music-Assist
Handles document retrieval, embedding, and LLM interaction
"""

import os
import json
from typing import List, Dict, Optional
from datetime import datetime
import asyncio

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# Import web search capabilities
from web_search import ChurchMusicWebSearch, is_music_related_question


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline for Music-Assist
    """
    
    def __init__(
        self,
        vector_db_path: str = "./data/vector_store",
        model_name: str = "gpt-3.5-turbo",
        chunk_size: int = 1200,  # Increased from 1000 for better context preservation
        chunk_overlap: int = 300  # Increased from 200 to avoid losing connections between chunks
    ):
        self.vector_db_path = vector_db_path
        self.model_name = model_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize components
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=0.1,  # Very low temperature for maximum factual accuracy
            max_tokens=1000,  # Increased token limit for comprehensive answers
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Improved text splitter with better separators for preserving context
        # Separators ordered by preference - tries to break at natural boundaries
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n\n",      # Double newline (paragraph breaks) - best
                "\n",        # Single newline - good
                ". ",        # Sentence end - acceptable
                "? ",        # Question end - acceptable
                "! ",        # Exclamation end - acceptable
                "; ",        # Semicolon - helps with lists
                ", ",        # Comma - for long sentences
                " ",         # Space - last resort
                ""           # Character level - absolute fallback
            ],
            keep_separator=True,  # Preserve separators to maintain readability
            length_function=len
        )
        
        self.vector_store = None
        self.qa_chain = None
        self.conversations = {}
        
        # Initialize web search
        self.web_searcher = ChurchMusicWebSearch()
        
    async def initialize(self):
        """Initialize or load vector store"""
        try:
            # Try to load existing vector store - check for actual index file
            index_file = os.path.join(self.vector_db_path, "index.faiss")
            abs_path = os.path.abspath(index_file)
            
            loaded = False
            if os.path.exists(index_file):
                try:
                    self.vector_store = FAISS.load_local(
                        self.vector_db_path,
                        self.embeddings,
                        allow_dangerous_deserialization=True
                    )
                    print(f"[OK] Loaded existing vector store from {abs_path}")
                    loaded = True
                except Exception as e:
                    print(f"[WARNING] Error loading existing vector store: {e}")

            if not loaded:
                print(f"! No usable vector store found at: {abs_path}")
                print("! Please run 'python populate_db.py' and ensure Phase 2 completes successfully.")
                # Create empty vector store as fallback
                try:
                    self.vector_store = FAISS.from_texts(
                        ["Initial placeholder document"],
                        self.embeddings,
                        metadatas=[{"source": "system", "type": "placeholder"}]
                    )
                except Exception as e:
                    print(f"[WARNING] Could not create placeholder vector store: {e}")
                    print("  Server will start in limited mode (IN-MEMORY ONLY) until crawler is run")
                    self.vector_store = None
                
            # Initialize QA chain (if vector store available)
            if self.vector_store:
                self._initialize_qa_chain()
            
        except Exception as e:
            print(f"Error initializing RAG pipeline: {e}")
            # Don't raise; allow server to start so /crawl/trigger can be used
    
    def _initialize_qa_chain(self):
        """Initialize the conversational QA chain using LCEL"""
        
        # Create retriever with optimized search for maximum answer coverage
        # MMR (Maximal Marginal Relevance) finds diverse relevant results
        # fetch_k=30 means: search through 30 candidates to ensure we find answers
        # k=10 means: return top 10 most relevant chunks (increased for comprehensive coverage)
        # lambda_mult=0.5 means: 50/50 balance between relevance and diversity
        #   - Lower lambda = more diversity (catches related topics)
        #   - Higher lambda = more similarity (focuses on exact matches)
        retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": 10,           # Return 10 chunks instead of 8
                "fetch_k": 30,     # Search through 30 candidates instead of 20
                "lambda_mult": 0.5 # More diversity to catch related information
            }
        )
        
        # Educational prompt template - teaches music theory and hymn concepts
        qa_system_prompt = """You are Music-Assist, a patient and encouraging MUSIC THEORY TEACHER specializing in LDS hymns and choir music. Your mission is to help beginners understand music concepts in friendly, practical ways.

TEACHING APPROACH - You are an educator, not just an answer bot:

1. **TEACH, DON'T JUST TELL**:
   - EXPLAIN concepts clearly, as if speaking to a beginner
   - Use SIMPLE LANGUAGE and avoid jargon (or define it)
   - Give EXAMPLES from actual LDS hymns when possible
   - BREAK DOWN complex ideas into digestible steps
   - Use ANALOGIES and comparisons to make concepts relatable

2. **UNDERSTAND WHAT THEY'RE ASKING**:
   - Theory Question ("What is a chord?") → Teach the concept with examples
   - Hymn Question ("Analyze Hymn 136") → Break down its musical elements
   - Practical Question ("How do I transpose?") → Step-by-step instructions
   - Policy Question ("Can youth be music leader?") → Provide handbook guidelines

3. **STRUCTURED EXPLANATIONS**:
   - Start with a simple definition or direct answer
   - Explain WHY it matters or how it works
   - Give CONCRETE EXAMPLES from LDS hymns (e.g., "In Hymn 136...")
   - Include practical tips for application
   - End with encouragement or next steps

4. **USE HYMN EXAMPLES**:
   - Reference specific hymn numbers when illustrating concepts
   - Example: "A major chord sounds bright and happy, like the opening of 'I Know That My Redeemer Lives' (Hymn 136)"
   - Make abstract concepts concrete through familiar hymns

5. **BE BEGINNER-FRIENDLY**:
   - Assume they're learning from scratch
   - Define musical terms inline: "A chord (3+ notes played together)..."
   - Use everyday comparisons: "Think of scales like a musical alphabet..."
   - Encourage: "This is a common question!" or "Great question!"

6. **CITE SOURCES CLEARLY**:
   - After teaching from source material, cite it
   - Format: (Source: Music Notation Basics) or (see General Handbook 19.4.3)
   - End with: "References: [list all sources]"

7. **WHEN YOU DON'T KNOW**:
   - Be honest: "I don't have specific information about that in my training materials"
   - Offer what you DO know that's related
   - Suggest: "For more details, consult [relevant resource]"
   - Stay focused on Church music topics

8. **ORGANIZE YOUR TEACHING**:
   - **Definition/Concept**: What is it?
   - **Explanation**: How does it work?
   - **Examples**: Show it in real hymns
   - **Application**: How to use it practically
   - **References**: Where this information comes from

REMEMBER: You're helping people learn music so they can better worship through hymns. Be patient, clear, and encouraging. Even complex concepts can be understood with good teaching!
   - Use clear structure

9. VERIFY BEFORE ANSWERING: 
   - Does your answer match what the user actually asked?
   - Did you cite sources for every major claim?
   - Did you include the References section?

===== CONTEXT FROM CHURCH MUSIC RESOURCES =====
{context}
===== END OF CONTEXT =====

User Question: {question}

Answer (directly address what the user asked, cite sources inline, end with References section):"""

        qa_prompt = PromptTemplate(
            template=qa_system_prompt,
            input_variables=["context", "question"]
        )
        
        # Enhanced document formatter - includes source information for better context
        def format_docs(docs):
            """Format retrieved documents with metadata for richer context"""
            formatted_parts = []
            for i, doc in enumerate(docs, 1):
                # Extract metadata
                source = doc.metadata.get('source', 'Unknown source')
                title = doc.metadata.get('title', '')
                
                # Format with source info for better AI understanding
                doc_text = f"[Passage {i}]"
                if title:
                    doc_text += f" From: {title}"
                if source and not source.startswith('system'):
                    doc_text += f" (Source: {source})"
                doc_text += f"\n{doc.page_content.strip()}"
                
                formatted_parts.append(doc_text)
            
            return "\n\n---\n\n".join(formatted_parts)
        
        # Build LCEL chain
        self.qa_chain = (
            {
                "context": retriever | format_docs,
                "question": RunnablePassthrough()
            }
            | qa_prompt
            | self.llm
            | StrOutputParser()
        )
    
    async def query(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict:
        """
        Process a user query through the RAG pipeline with hybrid search
        1. Check if question is music-related
        2. Search local vector store
        3. If insufficient → search Church websites
        4. Combine results and answer
        """
        try:
            # STEP 1: Validate topic - is this a music question?
            if not is_music_related_question(query):
                return {
                    "answer": "I'm Music-Assist, specialized in Church of Jesus Christ of Latter-day Saints music topics. I can help with hymns, choirs, music callings, sacred music guidelines, and music theory. However, your question appears to be outside my area of expertise. Please ask me about Church music topics!",
                    "sources": [],
                    "conversation_id": conversation_id or "none",
                    "search_method": "off-topic"
                }
            
            # Auto-recovery: If chain is missing, try to load it again (maybe DB was just built)
            if self.qa_chain is None:
                await self.initialize()

            if self.qa_chain is None:
                return {
                    "answer": "Vector store not initialized. Please run the crawler first to populate the knowledge base.",
                    "sources": [],
                    "conversation_id": conversation_id or "none",
                    "search_method": "error"
                }
            
            # Generate conversation ID if not provided
            if not conversation_id:
                conversation_id = f"conv_{datetime.utcnow().timestamp()}"
            
            # Get or create conversation history
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = []
            
            # STEP 2: Try local vector store first
            local_docs = await self._search_local(query)
            
            # STEP 3: Check if local results are sufficient
            needs_web_search = self._should_search_web(query, local_docs)
            
            web_results = []
            if needs_web_search:
                print(f"[INFO] Local data insufficient, searching Church websites...")
                web_results = await self.web_searcher.search(query)
                print(f"[INFO] Found {len(web_results)} web results")
            
            # STEP 4: Combine local + web context
            combined_context = self._combine_contexts(local_docs, web_results)
            
            # STEP 5: Generate answer with combined context
            result = await self._generate_answer(query, combined_context)
            
            # Track search method used
            if web_results:
                search_method = "hybrid (local + web)"
            else:
                search_method = "local only"
            
            # Update conversation history
            self.conversations[conversation_id].append((query, result))
            
            # Keep only last 10 exchanges to manage memory
            if len(self.conversations[conversation_id]) > 10:
                self.conversations[conversation_id] = self.conversations[conversation_id][-10:]
            
            return {
                "answer": result,
                "sources": self._extract_sources(local_docs, web_results),
                "conversation_id": conversation_id,
                "search_method": search_method
            }
            
        except Exception as e:
            print(f"Error processing query: {e}")
            raise
    
    async def add_documents(self, documents: List[Dict]):
        """
        Add new documents to the vector store
        
        Args:
            documents: List of dicts with 'content' and 'metadata' keys
        """
        try:
            # Convert to LangChain Document objects
            docs = []
            for doc in documents:
                docs.append(Document(
                    page_content=doc["content"],
                    metadata=doc.get("metadata", {})
                ))
            
            # Split documents into chunks
            splits = self.text_splitter.split_documents(docs)
            
            # Add to vector store
            if self.vector_store is None:
                self.vector_store = FAISS.from_documents(splits, self.embeddings)
            else:
                self.vector_store.add_documents(splits)
            
            # Save vector store
            self.vector_store.save_local(self.vector_db_path)
            
            abs_path = os.path.abspath(self.vector_db_path)
            print(f"[OK] Added {len(documents)} documents ({len(splits)} chunks)")
            print(f"[OK] Saved vector store to: {abs_path}")
            
            # Reinitialize QA chain with updated vector store
            self._initialize_qa_chain()
            
        except Exception as e:
            if "insufficient_quota" in str(e) or "429" in str(e):
                print("\n" + "!"*60)
                print("CRITICAL ERROR: OpenAI API Quota Exceeded")
                print("1. Go to https://platform.openai.com/settings/organization/billing")
                print("2. Add credits to your balance (API is separate from ChatGPT Plus)")
                print("!"*60 + "\n")
            print(f"Error adding documents: {e}")
            raise
    
    async def rebuild_vector_store(self):
        """
        Rebuild vector store from crawled documents
        """
        try:
            crawled_dir = "./data/crawled"
            
            if not os.path.exists(crawled_dir):
                raise ValueError(f"Crawled data directory not found: {crawled_dir}")
            
            documents = []
            
            # Load all crawled JSON files
            for filename in os.listdir(crawled_dir):
                if filename.endswith(".json"):
                    with open(os.path.join(crawled_dir, filename), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        documents.append({
                            "content": data.get("content", ""),
                            "metadata": {
                                "source": data.get("url", ""),
                                "title": data.get("title", ""),
                                "timestamp": data.get("timestamp", "")
                            }
                        })
            
            if not documents:
                raise ValueError("No documents found to index")
            
            # Rebuild vector store
            await self.add_documents(documents)
            
            return {"status": "success", "documents_indexed": len(documents)}
            
        except Exception as e:
            print(f"Error rebuilding vector store: {e}")
            raise
    
    async def get_stats(self) -> Dict:
        """Get pipeline statistics"""
        try:
            stats = {
                "vector_store_exists": self.vector_store is not None,
                "active_conversations": len(self.conversations),
                "model": self.model_name,
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap
            }
            
            if self.vector_store:
                stats["total_documents"] = self.vector_store.index.ntotal
            
            return stats
            
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {"error": str(e)}
    
    async def _search_local(self, query: str) -> List[Document]:
        """Search local vector store"""
        try:
            retriever = self.vector_store.as_retriever(
                search_type="mmr",
                search_kwargs={
                    "k": 10,
                    "fetch_k": 30,
                    "lambda_mult": 0.5
                }
            )
            
            docs = await asyncio.to_thread(
                retriever.invoke,
                query
            )
            
            return docs
            
        except Exception as e:
            print(f"[WARNING] Local search error: {e}")
            return []
    
    def _should_search_web(self, query: str, local_docs: List[Document]) -> bool:
        """
        Determine if web search is needed based on local results quality
        
        Returns True if:
        - No local results found
        - Local results seem incomplete or low quality
        - Query asks about specific people/names not in local data
        """
        # No local docs → definitely search web
        if not local_docs:
            return True
        
        # Check if query is about a specific person (likely not in local data)
        person_indicators = ['who is', 'who are', 'biography', 'composer', 'arranger', 
                            'wilberg', 'mark wilberg', 'mack wilberg']
        query_lower = query.lower()
        if any(indicator in query_lower for indicator in person_indicators):
            # Check if local docs actually mention the person
            query_terms = query_lower.split()
            name_terms = [term for term in query_terms if len(term) > 3 and term.isalpha()]
            
            local_content = ' '.join([doc.page_content.lower() for doc in local_docs[:3]])
            
            # If key name terms not found in top docs, search web
            if name_terms and not any(term in local_content for term in name_terms):
                return True
        
        # Check content quality - if top doc is very short, might need more
        if local_docs and len(local_docs[0].page_content) < 200:
            return True
        
        # Otherwise, local data is sufficient
        return False
    
    def _combine_contexts(self, local_docs: List[Document], web_results: List[Dict]) -> str:
        """
        Combine local vector store results with web search results
        
        Returns: Formatted context string for LLM
        """
        context_parts = []
        
        # Add local documents first (most reliable)
        if local_docs:
            context_parts.append("=== FROM LOCAL KNOWLEDGE BASE ===\n")
            for i, doc in enumerate(local_docs, 1):
                source = doc.metadata.get('source', 'Unknown')
                title = doc.metadata.get('title', '')
                
                doc_text = f"[Local Source {i}]"
                if title:
                    doc_text += f" {title}"
                if source and not source.startswith('system'):
                    doc_text += f" ({source})"
                doc_text += f"\n{doc.page_content.strip()}"
                
                context_parts.append(doc_text)
        
        # Add web results (supplementary)
        if web_results:
            context_parts.append("\n\n=== FROM CHURCH WEBSITES (RECENT SEARCH) ===\n")
            for i, result in enumerate(web_results, 1):
                web_text = f"[Web Source {i}] {result['title']}"
                web_text += f"\nURL: {result['url']}"
                web_text += f"\n{result['content']}"
                
                context_parts.append(web_text)
        
        return "\n\n---\n\n".join(context_parts)
    
    async def _generate_answer(self, query: str, context: str) -> str:
        """Generate answer using LLM with provided context"""
        try:
            # Enhanced prompt for hybrid search
            prompt = f"""You are Music-Assist, an expert assistant specializing in music theory, hymns, and choir music of The Church of Jesus Christ of Latter-day Saints.

CRITICAL INSTRUCTIONS - You MUST follow these rules:

1. UNDERSTAND THE QUESTION TYPE:
   - If user asks "WHAT [specific things]" (e.g., "what hymns", "what songs") → They want SPECIFIC NAMES/TITLES/LISTS
   - If user asks "WHO" → They want information about a PERSON
   - If user asks "HOW" or "WHY" → They want PROCEDURES/GUIDELINES/EXPLANATIONS
   - Answer the ACTUAL question asked, not related topics

2. READ ALL CONTEXT: Read EVERY passage below before answering. Context may include:
   - Local knowledge base (most reliable, curated data)
   - Recent web searches (for people, current information not in local data)

3. PRIORITIZE INFORMATION:
   - Local knowledge base is most authoritative
   - Web sources supplement when local data is insufficient
   - Always prefer official Church sources

4. **ALWAYS CITE YOUR SOURCES**:
   - After EVERY claim or fact, add a reference in parentheses
   - For local sources: cite as (see [document title or handbook section])
   - For web sources: cite as (Source: [website title], [URL])
   - End your answer with: "References: [list all sources used]"

5. BE HONEST WHEN MISSING SPECIFICS:
   - If user asks for specific items but context only has guidelines, say:
     "I don't have a specific list in my resources, but here are the guidelines: [guidelines]"
   - Don't give guidelines when user wants specific items unless you clearly state the limitation first

6. EXTRACT ALL RELEVANT INFORMATION from context

7. ORGANIZE YOUR ANSWER:
   - Start with the direct answer to the question
   - Add citations inline as you make claims
   - End with a "References:" section listing all sources
   - Use clear structure

8. VERIFY BEFORE ANSWERING: 
   - Does your answer match what the user actually asked?
   - Did you cite sources for every major claim?
   - Did you include the References section?

===== CONTEXT =====
{context}
===== END OF CONTEXT =====

User Question: {query}

Answer (directly address what the user asked, cite sources inline, end with References section):"""

            response = await asyncio.to_thread(
                self.llm.invoke,
                prompt
            )
            
            # Extract text from AIMessage
            if hasattr(response, 'content'):
                return response.content
            return str(response)
            
        except Exception as e:
            print(f"[ERROR] Answer generation failed: {e}")
            return "I encountered an error generating an answer. Please try rephrasing your question."
    
    def _extract_sources(self, local_docs: List[Document], web_results: List[Dict]) -> List[Dict]:
        """Extract source information for response metadata"""
        sources = []
        
        # Add local sources
        for doc in local_docs[:5]:  # Top 5 local sources
            sources.append({
                'type': 'local',
                'title': doc.metadata.get('title', 'Unknown'),
                'source': doc.metadata.get('source', 'Unknown')
            })
        
        # Add web sources
        for result in web_results:
            sources.append({
                'type': 'web',
                'title': result['title'],
                'url': result['url'],
                'relevance': result.get('relevance_score', 0)
            })
        
        return sources