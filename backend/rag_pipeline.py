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
    'MAX_CONTEXT_LENGTH': 8000, # Increased for more detailed fact-finding
    'MAX_RETRIES': 2,
    'RETRY_BASE_DELAY': 1,
    'REQUEST_TIMEOUT': 45,
    'MAX_TOKENS': 1500,
    'TEMPERATURE': 0.1, # Lowered for strict factual precision
    'CHUNK_SIZE': 1200,
    'CHUNK_OVERLAP': 300, # Increased overlap for better continuity
    'MAX_CONVERSATION_HISTORY': 8,
    'TOP_K_RESULTS': 10, # Fetch more context blocks
    'FETCH_K_RESULTS': 20, # More diversity for MMR retrieval
    'MMR_LAMBDA': 0.5, # Balance relevance and diversity
    'MIN_CONTENT_LENGTH_FOR_LOCAL': 400,
    'MIN_DOC_LENGTH_FOR_WEB': 300,
    'COST_PER_1K_INPUT_TOKENS': 0.0005,
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
from firebase_memory import FirebaseConversationMemory


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
        self.memory = None # Conversation memory
        self._local_conversations = set() # Track active convos for stats
        
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

            # Initialize conversation memory
            if not self.memory:
                self.memory = FirebaseConversationMemory()
            
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
        #   - Higher lambda = more similarity
        retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": CONFIG['TOP_K_RESULTS'],
                "fetch_k": CONFIG['FETCH_K_RESULTS'],
                "lambda_mult": CONFIG['MMR_LAMBDA']
            }
        )
        
        # Educational prompt template - updated for conversational flow
        qa_system_prompt = """You are Music-Assist, a friendly and expert music teacher and consultant for members of The Church of Jesus Christ of Latter-day Saints.

=== YOUR PERSONALITY ===
- **Expertly Grounded**: You are a master of official Church music policy and the 1985 Hymnbook. 
- **Direct & Definitive**: Give specific numbers, names, and handbook sections (like "Handbook 19.4.2") whenever they appear in the source materials.
- **Conversational**: Chat naturally, but keep facts front and center.

=== GROUNDING RULES (VITAL) ===
1. **Context is King**: The information provided in the CONTEXT below is your primary source of truth. If the context provides a specific fact (e.g., "The hymnbook has 341 hymns"), do NOT say "it typically has many" or "it varies." Give the specific info directly.
2. **No Evasion**: Avoid "may vary" or "is generally" if the context offers a definitive rule or list.
3. **No Robotic Labels**: Deliver facts naturally. Instead of "(Source 1)", say "As noted in the General Handbook..." or "According to the hymn index...". NEVER use robotic tags.
4. **Accuracy Over Polish**: It is better to be brief and 100% accurate based on the context than to be long-winded and vague.

=== RESPONSE FORMAT ===
- Use simple HTML (p, b, br, ul, li).
- Keep it friendly, professional, and fact-focused.

=== CONTEXT FROM CHURCH MUSIC RESOURCES ===
{context}
=== END OF CONTEXT ===

User Question: {question}

Answer (Conversationally expert and strictly grounded in the context facts):"""

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
            
            self._local_conversations.add(conversation_id)
            
            # Extract music-specific context (hymn numbers, terminology)
            music_context = self._extract_music_context(query)
            if music_context:
                logger.info(f"Detected music context: {music_context}")
            
            # Get conversation history for context from Firebase/memory
            conversation_history_str = await self._get_formatted_conversation_history(conversation_id)
            
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
            
            # STEP 4.5: Calculate confidence level for this query
            confidence_level = self._calculate_confidence(local_docs, web_results, query)
            
            # STEP 5: Generate answer with combined context
            gen_start = time.time()
            result = await self._generate_answer(query, combined_context, conversation_history_str)
            metrics['generation_time_ms'] = int((time.time() - gen_start) * 1000)
            
            # STEP 5.5: Add confidence disclaimer if needed
            if confidence_level == "low":
                result = self._add_confidence_disclaimer(result, "low", web_results)
            elif confidence_level == "medium" and web_results:
                result = self._add_confidence_disclaimer(result, "medium", web_results)
            
            # Estimate tokens and cost
            input_text = combined_context + query + conversation_history_str
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
            
            # Update conversation history in Firestore
            await asyncio.to_thread(self.memory.add_message, conversation_id, query, result, user_id)
            
            # Calculate total response time
            response_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Query completed: {response_time_ms}ms, cost=${metrics['cost_usd']}, method={search_method}, confidence={confidence_level}")
            
            return {
                "answer": result,
                "sources": self._extract_sources(local_docs, web_results),
                "conversation_id": conversation_id,
                "search_method": search_method,
                "confidence": confidence_level,
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
                    "confidence_level": confidence_level,
                    "conversation_length": len(conversation_history_str.split('\n\n')) if conversation_history_str else 1,
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
        # In a containerized/serverless environment, the filesystem is often read-only.
        # This check prevents attempts to write to it at runtime.
        if os.getenv("ENVIRONMENT") == "production":
            logger.warning("Cannot add documents in a read-only production environment.")
            raise PermissionError("The knowledge base cannot be modified at runtime in this environment.")

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
        if os.getenv("ENVIRONMENT") == "production":
            logger.warning("Cannot rebuild vector store in a read-only production environment.")
            raise PermissionError("The knowledge base cannot be modified at runtime in this environment.")

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
                "active_conversations_in_session": len(self._local_conversations),
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
                    "k": CONFIG['TOP_K_RESULTS'],
                    "fetch_k": CONFIG['FETCH_K_RESULTS'],
                    "lambda_mult": CONFIG['MMR_LAMBDA']
                }
            )
            
            # Use invoke for LangChain retriever (get_relevant_documents is deprecated)
            docs = await asyncio.to_thread(
                retriever.invoke,
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
    
    def _calculate_confidence(self, local_docs: List[Document], web_results: List[Dict], query: str) -> str:
        """
        Calculate confidence level for the response.
        
        Returns: 'high', 'medium', or 'low'
        
        Confidence is determined by:
        - Number and quality of local sources
        - Whether web fallback was needed
        - Type of question (factual vs. conceptual)
        """
        query_lower = query.lower()
        
        # Check if this is a high-risk factual question (composer, dates, etc.)
        is_factual_query = any(term in query_lower for term in [
            'who composed', 'who wrote', 'composer', 'lyricist', 'author',
            'when was', 'what year', 'date', 'history of', 'origin'
        ])
        
        # High confidence: Good local sources, no web fallback needed
        if len(local_docs) >= 3 and not web_results:
            # Check if local docs have substantial content
            avg_length = sum(len(d.page_content) for d in local_docs[:3]) / 3
            if avg_length > CONFIG['MIN_CONTENT_LENGTH_FOR_LOCAL']:
                return "high"
        
        # Medium confidence: Some local sources, or good web results
        if len(local_docs) >= 1 or len(web_results) >= 2:
            # Factual queries with web fallback are medium confidence
            if is_factual_query and web_results:
                return "medium"
            return "medium" if web_results else "high"
        
        # Low confidence: Very few sources
        return "low"
    
    def _add_confidence_disclaimer(self, response: str, confidence: str, web_results: List[Dict]) -> str:
        """
        Add appropriate confidence disclaimer to the response.
        
        This helps users understand the reliability of the information.
        """
        if confidence == "low":
            disclaimer = (
                "\n\n---\n"
                "⚠️ **Note:** This response is based on limited source material. "
                "For authoritative information, please consult the official Church Music Library "
                "or General Handbook."
            )
            return response + disclaimer
        
        elif confidence == "medium" and web_results:
            disclaimer = (
                "\n\n---\n"
                "ℹ️ **Note:** This answer incorporates information from broader Church website sources "
                "in addition to the curated knowledge base."
            )
            return response + disclaimer
        
        return response
    
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
                
                prompt = f"""You are Music-Assist, a friendly and expert music teacher and consultant for members of The Church of Jesus Christ of Latter-day Saints.{conversation_context}

=== YOUR PERSONALITY ===
- **Expertly Grounded**: You are a master of official Church music policy and the 1985 Hymnbook. 
- **Direct & Definitive**: Give specific numbers, names, and handbook sections (like "Handbook 19.4.2") whenever they appear in the source materials.
- **Conversational**: Chat naturally, but keep facts front and center.

=== GROUNDING RULES (VITAL) ===
1. **Context is King**: The information provided in the CONTEXT below is your primary source of truth. If the context has a specific fact, give it directly. NEVER say "it typically has many" or "it varies" if the context provides a number.
2. **No Evasion**: Avoid "may vary" or "is generally" if the context offers a definitive rule.
3. **Accuracy Over Polish**: It is better to be brief and 100% accurate based on the context than to be long-winded and vague.

=== CONTEXT FROM CHURCH MUSIC RESOURCES ===
{context}
=== END OF CONTEXT ===

User Question: {query}

Answer (Conversationally expert and strictly grounded in the context facts):"""

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
    
    async def _get_formatted_conversation_history(self, conversation_id: str, max_exchanges: int = 3) -> str:
        """Format recent conversation history for context."""
        if not self.memory:
            return ""
        
        # Fetch history from Firestore/memory in a non-blocking way
        history = await asyncio.to_thread(self.memory.get_history, conversation_id)
        if not history:
            return ""
        
        # Get last N exchanges (history from memory is already ordered and limited)
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