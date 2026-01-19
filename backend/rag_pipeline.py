"""
RAG Pipeline for Music-Assist
Handles document retrieval, embedding, and LLM interaction
"""

import os
import json
import time
import logging
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Production Configuration Constants
CONFIG = {
    'MAX_CONTEXT_LENGTH': 6000,  # Characters (~1500 tokens)
    'MAX_RETRIES': 3,
    'RETRY_BASE_DELAY': 2,  # seconds
    'REQUEST_TIMEOUT': 60,  # seconds
    'MAX_TOKENS': 1500,
    'TEMPERATURE': 0.1,
    'CHUNK_SIZE': 1200,
    'CHUNK_OVERLAP': 300,
    'MAX_CONVERSATION_HISTORY': 10,
    'TOP_K_RESULTS': 10,
    'FETCH_K_RESULTS': 30,
    'MMR_LAMBDA': 0.5,
    'MIN_CONTENT_LENGTH_FOR_LOCAL': 500,  # chars for trusting local data
    'MIN_DOC_LENGTH_FOR_WEB': 200,  # chars before triggering web search
    'COST_PER_1K_INPUT_TOKENS': 0.0005,  # GPT-3.5-turbo pricing
    'COST_PER_1K_OUTPUT_TOKENS': 0.0015,
}

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
    Production-grade Retrieval-Augmented Generation pipeline for Music-Assist.
    
    Specialized for LDS Church music education, providing accurate information about:
    - Hymns and sacred music
    - Music theory fundamentals
    - Choir and music calling guidelines
    - Music notation and performance
    
    Features:
    - Hybrid search (local vector store + web search)
    - Conversation context awareness
    - Cost tracking and monitoring
    - Automatic retry with exponential backoff
    - Input validation and sanitization
    - Comprehensive error handling
    """
    
    def __init__(
        self,
        vector_db_path: str = "./data/vector_store",
        model_name: str = "gpt-3.5-turbo",
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        """Initialize RAG pipeline with production configuration."""
        self.vector_db_path = vector_db_path
        self.model_name = model_name
        self.chunk_size = chunk_size or CONFIG['CHUNK_SIZE']
        self.chunk_overlap = chunk_overlap or CONFIG['CHUNK_OVERLAP']
        
        # Cost tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_queries = 0
        self.failed_queries = 0
        
        # Initialize components
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=CONFIG['TEMPERATURE'],
            max_tokens=CONFIG['MAX_TOKENS'],
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            request_timeout=CONFIG['REQUEST_TIMEOUT']
        )
        
        logger.info(f"Initialized RAG Pipeline: model={model_name}, max_tokens={CONFIG['MAX_TOKENS']}")
        
        # Improved text splitter with better separators for preserving context
        # Separators ordered by preference - tries to break at natural boundaries
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
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
                    logger.info(f"Loaded existing vector store from {abs_path}")
                    loaded = True
                except Exception as e:
                    logger.warning(f"Error loading existing vector store: {e}")

            if not loaded:
                logger.warning(f"No usable vector store found at: {abs_path}")
                logger.warning("Please run 'python populate_db.py' and ensure Phase 2 completes successfully.")
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
                "k": CONFIG['TOP_K_RESULTS'],
                "fetch_k": CONFIG['FETCH_K_RESULTS'],
                "lambda_mult": CONFIG['MMR_LAMBDA']
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
        Process a user query through the production RAG pipeline.
        
        Args:
            query: User's question (will be validated and sanitized)
            conversation_id: Optional conversation ID for context
            user_id: Optional user ID for tracking
            
        Returns:
            Dict containing answer, sources, metrics, and conversation_id
            
        Raises:
            ValueError: If query is invalid
            Exception: For system errors (logged and handled gracefully)
        """
        # Track performance and cost metrics
        start_time = time.time()
        metrics = {
            'local_docs_count': 0,
            'web_results_count': 0,
            'input_tokens_estimated': 0,
            'output_tokens_estimated': 0,
            'search_time_ms': 0,
            'generation_time_ms': 0,
            'cost_usd': 0.0
        }
        
        try:
            # STEP 0: Input validation and sanitization
            query = self._validate_and_sanitize_input(query)
            self.total_queries += 1
            logger.info(f"Processing query (conv_id={conversation_id}): {query[:100]}...")
            
            # STEP 1: Validate topic - is this a music question?
            if not is_music_related_question(query):
                logger.info(f"Off-topic query detected: {query[:50]}")
                return {
                    "answer": "I'm Music-Assist, specialized in Church of Jesus Christ of Latter-day Saints music topics. I can help with hymns, choirs, music callings, sacred music guidelines, and music theory. However, your question appears to be outside my area of expertise. Please ask me about Church music topics!",
                    "sources": [],
                    "conversation_id": conversation_id or "none",
                    "search_method": "off-topic",
                    "metrics": {
                        "response_time_ms": int((time.time() - start_time) * 1000),
                        "local_chunks_retrieved": 0,
                        "web_results_retrieved": 0,
                        "estimated_tokens": 0,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            
            # Auto-recovery: If chain is missing, try to load it again (maybe DB was just built)
            if self.qa_chain is None:
                await self.initialize()

            if self.qa_chain is None:
                return {
                    "answer": (
                        "⚠️ **Knowledge Base Not Initialized**\n\n"
                        "The AI assistant needs to index the Church music resources first.\n\n"
                        "**To fix this:**\n"
                        "1. Run: `python populate_db.py`\n"
                        "2. Wait for 'Phase 2: Complete' message (may take 10-15 minutes)\n"
                        "3. Ensure you have OpenAI API credits at: https://platform.openai.com/settings/organization/billing\n"
                        "4. Try your question again\n\n"
                        "**Current status:** Vector store file not found or corrupted\n"
                        "**Need help?** Check the README.md for detailed setup instructions."
                    ),
                    "sources": [],
                    "conversation_id": conversation_id or "none",
                    "search_method": "error",
                    "error_code": "VECTOR_STORE_NOT_INITIALIZED"
                }
            
            # Generate conversation ID if not provided
            if not conversation_id:
                conversation_id = f"conv_{datetime.utcnow().timestamp()}"
            
            # Get or create conversation history
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = []
            
            # Extract music-specific context (hymn numbers, terminology)
            music_context = self._extract_music_context(query)
            if music_context:
                logger.info(f"Detected music context: {music_context}")
            
            # Get conversation history for context
            conversation_history = self._format_conversation_history(conversation_id)
            
            # STEP 2: Try local vector store first
            search_start = time.time()
            local_docs = await self._search_local(query)
            metrics['local_docs_count'] = len(local_docs)
            metrics['search_time_ms'] = int((time.time() - search_start) * 1000)
            
            # STEP 3: Check if local results are sufficient
            needs_web_search = self._should_search_web(query, local_docs)
            
            web_results = []
            if needs_web_search:
                print(f"[INFO] Local data insufficient, searching Church websites...")
                web_start = time.time()
                web_results = await self.web_searcher.search(query)
                metrics['web_results_count'] = len(web_results)
                metrics['search_time_ms'] += int((time.time() - web_start) * 1000)
                print(f"[INFO] Found {len(web_results)} web results")
            
            # STEP 4: Combine local + web context
            combined_context = self._combine_contexts(local_docs, web_results)
            
            # STEP 5: Generate answer with combined context
            gen_start = time.time()
            result = await self._generate_answer(query, combined_context)
            metrics['generation_time_ms'] = int((time.time() - gen_start) * 1000)
            
            # Estimate tokens and cost
            input_text = combined_context + query + conversation_history
            output_text = result
            metrics['input_tokens_estimated'] = int(len(input_text.split()) * 1.3)
            metrics['output_tokens_estimated'] = int(len(output_text.split()) * 1.3)
            
            # Calculate cost
            input_cost = (metrics['input_tokens_estimated'] / 1000) * CONFIG['COST_PER_1K_INPUT_TOKENS']
            output_cost = (metrics['output_tokens_estimated'] / 1000) * CONFIG['COST_PER_1K_OUTPUT_TOKENS']
            metrics['cost_usd'] = round(input_cost + output_cost, 6)
            
            # Update global cost tracking
            self.total_input_tokens += metrics['input_tokens_estimated']
            self.total_output_tokens += metrics['output_tokens_estimated']
            
            # Track search method used
            if web_results:
                search_method = "hybrid (local + web)"
            else:
                search_method = "local only"
            
            # Update conversation history
            self.conversations[conversation_id].append((query, result))
            
            # Keep only last N exchanges to manage memory
            if len(self.conversations[conversation_id]) > CONFIG['MAX_CONVERSATION_HISTORY']:
                self.conversations[conversation_id] = self.conversations[conversation_id][-CONFIG['MAX_CONVERSATION_HISTORY']:]
            
            # Calculate total response time
            response_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Query completed: {response_time_ms}ms, cost=${metrics['cost_usd']}, method={search_method}")
            
            return {
                "answer": result,
                "sources": self._extract_sources(local_docs, web_results),
                "conversation_id": conversation_id,
                "search_method": search_method,
                "music_context": music_context,
                "metrics": {
                    "response_time_ms": response_time_ms,
                    "search_time_ms": metrics['search_time_ms'],
                    "generation_time_ms": metrics['generation_time_ms'],
                    "local_chunks_retrieved": metrics['local_docs_count'],
                    "web_results_retrieved": metrics['web_results_count'],
                    "input_tokens_estimated": metrics['input_tokens_estimated'],
                    "output_tokens_estimated": metrics['output_tokens_estimated'],
                    "cost_usd": metrics['cost_usd'],
                    "conversation_length": len(self.conversations.get(conversation_id, [])),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
        except ValueError as e:
            # Input validation errors
            self.failed_queries += 1
            logger.warning(f"Invalid input: {e}")
            raise
        except Exception as e:
            self.failed_queries += 1
            logger.error(f"Error processing query: {e}", exc_info=True)
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
            logger.info(f"Added {len(documents)} documents ({len(splits)} chunks)")
            logger.info(f"Saved vector store to: {abs_path}")
            
            # Reinitialize QA chain with updated vector store
            self._initialize_qa_chain()
            
        except Exception as e:
            if "insufficient_quota" in str(e) or "429" in str(e):
                logger.critical("OpenAI API Quota Exceeded")
                logger.critical("1. Go to https://platform.openai.com/settings/organization/billing")
                logger.critical("2. Add credits to your balance (API is separate from ChatGPT Plus)")
            logger.error(f"Error adding documents: {e}", exc_info=True)
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
        """Get comprehensive pipeline statistics for monitoring."""
        try:
            # Calculate total cost
            total_input_cost = (self.total_input_tokens / 1000) * CONFIG['COST_PER_1K_INPUT_TOKENS']
            total_output_cost = (self.total_output_tokens / 1000) * CONFIG['COST_PER_1K_OUTPUT_TOKENS']
            total_cost = total_input_cost + total_output_cost
            
            stats = {
                "status": "healthy" if self.vector_store is not None else "degraded",
                "vector_store_exists": self.vector_store is not None,
                "active_conversations": len(self.conversations),
                "model": self.model_name,
                "configuration": {
                    "chunk_size": self.chunk_size,
                    "chunk_overlap": self.chunk_overlap,
                    "max_tokens": CONFIG['MAX_TOKENS'],
                    "temperature": CONFIG['TEMPERATURE']
                },
                "usage": {
                    "total_queries": self.total_queries,
                    "failed_queries": self.failed_queries,
                    "success_rate": round((self.total_queries - self.failed_queries) / max(self.total_queries, 1) * 100, 2),
                    "total_input_tokens": self.total_input_tokens,
                    "total_output_tokens": self.total_output_tokens,
                    "total_cost_usd": round(total_cost, 4),
                    "avg_cost_per_query_usd": round(total_cost / max(self.total_queries, 1), 6)
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if self.vector_store:
                stats["total_documents"] = self.vector_store.index.ntotal
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def health_check(self) -> Dict:
        """Perform health check for production monitoring."""
        health = {
            "status": "healthy",
            "checks": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Check 1: Vector store
            if self.vector_store is None:
                health["checks"]["vector_store"] = {"status": "error", "message": "Not initialized"}
                health["status"] = "unhealthy"
            else:
                health["checks"]["vector_store"] = {"status": "ok", "documents": self.vector_store.index.ntotal}
            
            # Check 2: OpenAI API key
            if not os.getenv("OPENAI_API_KEY"):
                health["checks"]["openai_api"] = {"status": "error", "message": "API key not found"}
                health["status"] = "unhealthy"
            else:
                health["checks"]["openai_api"] = {"status": "ok", "message": "API key configured"}
            
            # Check 3: Web search
            if self.web_searcher:
                health["checks"]["web_search"] = {"status": "ok", "message": "Initialized"}
            else:
                health["checks"]["web_search"] = {"status": "warning", "message": "Not available"}
            
            # Check 4: Error rate
            if self.total_queries > 0:
                error_rate = (self.failed_queries / self.total_queries) * 100
                if error_rate > 10:
                    health["checks"]["error_rate"] = {"status": "warning", "rate": f"{error_rate:.2f}%"}
                    if health["status"] == "healthy":
                        health["status"] = "degraded"
                else:
                    health["checks"]["error_rate"] = {"status": "ok", "rate": f"{error_rate:.2f}%"}
            
            logger.info(f"Health check completed: {health['status']}")
            return health
            
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
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
            
            # Use get_relevant_documents for consistent List[Document] return
            docs = await asyncio.to_thread(
                retriever.get_relevant_documents,
                query
            )
            
            return docs
            
        except Exception as e:
            logger.warning(f"Local search error: {e}")
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
        
        # Check content quality first
        if local_docs:
            # Calculate average content length of top 3 results
            top_docs = local_docs[:3]
            avg_length = sum(len(doc.page_content) for doc in top_docs) / len(top_docs)
            
            # If we have substantial content, analyze further
            if avg_length > CONFIG['MIN_CONTENT_LENGTH_FOR_LOCAL']:
                # Combine content for analysis
                local_content = ' '.join([doc.page_content.lower() for doc in top_docs])
                
                # Check if query is about a specific person
                person_indicators = ['who is', 'who are', 'biography', 'composer', 'arranger']
                query_lower = query.lower()
                
                is_person_query = any(indicator in query_lower for indicator in person_indicators)
                
                if is_person_query:
                    # Extract potential name terms from query
                    query_terms = query_lower.split()
                    name_terms = [
                        term for term in query_terms 
                        if len(term) > 3 and term.isalpha() 
                        and term not in person_indicators
                    ]
                    
                    # If key name terms not found in local content → search web
                    if name_terms and not any(term in local_content for term in name_terms):
                        logger.info(f"Person query not found in local data - searching web")
                        return True
                    else:
                        logger.info(f"Person query found in local data - skipping web search")
                        return False
                else:
                    # For non-person queries, trust substantial local content
                    logger.info(f"Substantial local content found ({avg_length:.0f} chars avg) - skipping web search")
                    return False
        
        # FALLBACK: If top result is very short, might need supplementation
        if local_docs and len(local_docs[0].page_content) < CONFIG['MIN_DOC_LENGTH_FOR_WEB']:
            logger.info(f"Top result too short ({len(local_docs[0].page_content)} chars) - searching web")
            return True
        
        # Otherwise, local data is sufficient
        return False
    
    def _combine_contexts(self, local_docs: List[Document], web_results: List[Dict]) -> str:
        """
        Combine local vector store results with web search results
        
        Returns: Formatted context string for LLM
        """
        # Context length management to prevent token overflow
        MAX_CONTEXT_LENGTH = CONFIG['MAX_CONTEXT_LENGTH']
        current_length = 0
        context_parts = []
        
        # Add local documents first (most reliable)
        if local_docs:
            context_parts.append("=== FROM LOCAL KNOWLEDGE BASE ===\n")
            current_length += len(context_parts[0])
            
            for i, doc in enumerate(local_docs, 1):
                source = doc.metadata.get('source', 'Unknown')
                title = doc.metadata.get('title', '')
                
                doc_text = f"[Local Source {i}]"
                if title:
                    doc_text += f" {title}"
                if source and not source.startswith('system'):
                    doc_text += f" ({source})"
                doc_text += f"\n{doc.page_content.strip()}"
                
                # Check length before adding
                if current_length + len(doc_text) + 10 > MAX_CONTEXT_LENGTH:
                    remaining = len(local_docs) - i
                    context_parts.append(
                        f"\n[... {remaining} more local sources omitted due to length ...]"
                    )
                    logger.info(f"Context limit reached, omitted {remaining} local sources")
                    break
                
                context_parts.append(doc_text)
                current_length += len(doc_text) + 10  # +10 for separators
        
        # Add web results (supplementary) with length check
        if web_results and current_length < MAX_CONTEXT_LENGTH:
            web_section = "\n\n=== FROM CHURCH WEBSITES (RECENT SEARCH) ===\n"
            context_parts.append(web_section)
            current_length += len(web_section)
            
            for i, result in enumerate(web_results, 1):
                web_text = f"[Web Source {i}] {result['title']}"
                web_text += f"\nURL: {result['url']}"
                web_text += f"\n{result['content']}"
                
                # Check length before adding web results
                if current_length + len(web_text) + 10 > MAX_CONTEXT_LENGTH:
                    remaining = len(web_results) - i
                    context_parts.append(
                        f"\n[... {remaining} more web sources omitted due to length ...]"
                    )
                    logger.info(f"Context limit reached, omitted {remaining} web sources")
                    break
                
                context_parts.append(web_text)
                current_length += len(web_text) + 10
        
        final_context = "\n\n---\n\n".join(context_parts)
        
        # Final safety check
        if len(final_context) > MAX_CONTEXT_LENGTH:
            final_context = final_context[:MAX_CONTEXT_LENGTH] + "\n\n[Context truncated to fit token limit]"
            logger.warning(f"Context exceeded limit, truncated to {MAX_CONTEXT_LENGTH} chars")
        
        return final_context
    
    async def _generate_answer(self, query: str, context: str, conversation_history: str = "") -> str:
        """Generate answer using LLM with provided context and conversation history."""
        # Retry logic for transient failures
        max_retries = CONFIG['MAX_RETRIES']
        retry_delay = CONFIG['RETRY_BASE_DELAY']
        
        for attempt in range(max_retries):
            try:
                # Validate context before expensive LLM call
                if not context or context.strip() == "":
                    return (
                        "I don't have enough information in my knowledge base to answer this question accurately. "
                        "This might mean:\n"
                        "1. The topic isn't covered in my training materials\n"
                        "2. The knowledge base needs to be updated\n"
                        "3. Try rephrasing your question with different keywords\n\n"
                        "I specialize in LDS hymns, music theory, and church music guidelines. "
                        "Please ask a related question!"
                    )
                
                # Enhanced prompt with conversation context
                conversation_context = ""
                if conversation_history:
                    conversation_context = f"""\n===== CONVERSATION HISTORY =====
{conversation_history}
===== END CONVERSATION HISTORY =====\n\n"""
                
                prompt = f"""You are Music-Assist, an expert assistant specializing in music theory, hymns, and choir music of The Church of Jesus Christ of Latter-day Saints.{conversation_context}
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
                error_str = str(e).lower()
                
                # Handle rate limits with exponential backoff
                if ("rate_limit" in error_str or "429" in error_str) and attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential: 2s, 4s, 8s
                    logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue  # Try again
                
                # Handle timeout errors
                elif ("timeout" in error_str or "timed out" in error_str) and attempt < max_retries - 1:
                    logger.warning(f"Request timeout, retrying (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                    continue  # Try again
                
                # For other errors or last attempt, provide helpful message
                else:
                    logger.error(f"Answer generation failed: {e}")
                    
                    # Give user actionable error message based on error type
                    if "rate_limit" in error_str or "insufficient_quota" in error_str:
                        return (
                            "⚠️ **OpenAI API Quota Exceeded**\n\n"
                            "The system has reached its API usage limit. To resolve:\n"
                            "1. Go to https://platform.openai.com/settings/organization/billing\n"
                            "2. Add credits to your account ($5-10 is sufficient for testing)\n"
                            "3. Wait a few minutes for the system to update\n"
                            "4. Try your question again\n\n"
                            "Note: ChatGPT Plus subscription is separate from API credits."
                        )
                    
                    # Re-raise for other errors to be caught by outer handler
                    raise
        
        # Should never reach here due to raise in loop, but safety fallback
        return "I encountered an error generating an answer. Please try again later."
    
    def _extract_sources(self, local_docs: List[Document], web_results: List[Dict]) -> List[Dict]:
        """Extract source information for response metadata"""
        sources = []
        seen_urls = set()  # Track seen URLs to prevent duplicates
        
        # Add local sources
        for doc in local_docs[:5]:  # Top 5 local sources
            source_url = doc.metadata.get('source', 'Unknown')
            
            # Skip if we've already added this source
            if source_url in seen_urls:
                continue
            
            sources.append({
                'type': 'local',
                'title': doc.metadata.get('title', 'Unknown'),
                'source': source_url
            })
            seen_urls.add(source_url)
        
        # Add web sources
        for result in web_results:
            web_url = result.get('url', '')
            
            # Skip duplicates
            if web_url in seen_urls:
                continue
            
            sources.append({
                'type': 'web',
                'title': result['title'],
                'url': web_url,
                'relevance': result.get('relevance_score', 0)
            })
            seen_urls.add(web_url)
        
        return sources
    
    def _validate_and_sanitize_input(self, query: str) -> str:
        """Validate and sanitize user input for security and quality."""
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")
        
        # Strip whitespace
        query = query.strip()
        
        # Check length
        if len(query) < 3:
            raise ValueError("Query too short (minimum 3 characters)")
        
        if len(query) > 1000:
            logger.warning(f"Query too long ({len(query)} chars), truncating")
            query = query[:1000]
        
        # Remove excessive whitespace
        query = ' '.join(query.split())
        
        # Basic sanitization (remove potential injection attempts)
        # Remove null bytes
        query = query.replace('\x00', '')
        
        return query
    
    def _format_conversation_history(self, conversation_id: str, max_exchanges: int = 3) -> str:
        """Format recent conversation history for context."""
        if conversation_id not in self.conversations:
            return ""
        
        history = self.conversations[conversation_id]
        if not history:
            return ""
        
        # Get last N exchanges
        recent = history[-max_exchanges:]
        
        formatted = []
        for i, (q, a) in enumerate(recent, 1):
            # Truncate long answers to save tokens
            answer_preview = a[:200] + "..." if len(a) > 200 else a
            formatted.append(f"Previous Q{i}: {q}\nPrevious A{i}: {answer_preview}")
        
        return "\n\n".join(formatted)
    
    def _extract_music_context(self, query: str) -> Dict[str, any]:
        """Extract music-specific context from query (hymn numbers, terminology)."""
        context = {}
        
        # Extract hymn numbers
        hymn_pattern = r'\b(?:hymn|song|number)\s*#?\s*(\d{1,3})\b'
        hymn_matches = re.findall(hymn_pattern, query.lower())
        if hymn_matches:
            context['hymn_numbers'] = [int(h) for h in hymn_matches if 1 <= int(h) <= 341]
        
        # Detect music theory terms
        theory_terms = [
            'chord', 'scale', 'key', 'tempo', 'rhythm', 'harmony', 'melody',
            'notation', 'clef', 'treble', 'bass', 'sharps', 'flats', 'time signature',
            'dynamics', 'forte', 'piano', 'crescendo', 'diminuendo'
        ]
        found_terms = [term for term in theory_terms if term in query.lower()]
        if found_terms:
            context['theory_terms'] = found_terms
        
        # Detect specific callings/roles
        callings = ['music director', 'organist', 'pianist', 'choir director', 'music coordinator']
        found_callings = [calling for calling in callings if calling in query.lower()]
        if found_callings:
            context['callings'] = found_callings
        
        return context if context else None