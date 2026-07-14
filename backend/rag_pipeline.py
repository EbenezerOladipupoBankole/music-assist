"""
RAG Pipeline for Music-Assist
Handles document retrieval, embedding, and LLM interaction
"""

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Optional

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings
from interfaces import ConversationMemory
from web_search import ChurchMusicWebSearch, is_music_related_question

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        
        # Cost tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_queries = 0
        self.failed_queries = 0
        
        # Ensure OPENAI_API_KEY is available
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise ValueError("OPENAI_API_KEY environment variable is missing. It is required for RAG pipeline.")
            
        # Initialize components
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=openai_key
        )
        
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            openai_api_key=openai_key,
            request_timeout=settings.request_timeout
        )

        logger.info(f"Initialized RAG Pipeline: model={model_name}, max_tokens={settings.max_tokens}")
        
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
        self._ready = False  # True once vector_store is loaded and queryable
        self.memory: Optional[ConversationMemory] = None # Conversation memory - SQLite or Firestore
        self._local_conversations = set() # Track active convos for stats
        
        # Response cache for instant repeat queries (max 50 entries)
        self._response_cache = {}
        self._cache_max_size = 50
        
        # Initialize web search
        self.web_searcher = ChurchMusicWebSearch()
        
    async def initialize(self):
        """Initialize or load vector store"""
        try:
            # Initialize conversation memory backend per settings.memory_backend
            if not self.memory:
                if settings.memory_backend == "firebase":
                    from firebase_memory import FirebaseConversationMemory
                    self.memory = FirebaseConversationMemory()
                else:
                    from sqlite_memory import SQLiteConversationMemory
                    self.memory = SQLiteConversationMemory()

            # Try to load existing vector store - check for actual index file
            index_file = os.path.join(self.vector_db_path, "index.faiss")
            abs_path = os.path.abspath(index_file)
            
            loaded = False
            if os.path.exists(index_file):
                try:
                    # Safe here: this index is produced by our own rebuild_index.py /
                    # populate_db.py scripts, never uploaded by a user, so deserializing
                    # the pickled docstore carries no untrusted-input risk.
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
                    logger.warning(f"Could not create placeholder vector store: {e}")
                    logger.warning("Server will start in limited mode (IN-MEMORY ONLY) until crawler is run")
                    self.vector_store = None
                
            self._ready = self.vector_store is not None

        except Exception:
            logger.error("Error initializing RAG pipeline", exc_info=True)
            # Don't raise; allow server to start so /crawl/trigger can be used
    
    def _build_retriever(self):
        """MMR retriever over the vector store, tuned for max answer coverage.

        MMR (Maximal Marginal Relevance) finds diverse relevant results:
        fetch_k candidates are searched, the top k are returned, and lambda_mult
        balances relevance vs. diversity (lower = more diversity/related topics,
        higher = more strict similarity).
        """
        return self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": settings.top_k_results,
                "fetch_k": settings.fetch_k_results,
                "lambda_mult": settings.mmr_lambda,
            }
        )

    def _build_prompt(self, query: str, context: str, conversation_history: str = "") -> str:
        """Single prompt template shared by streaming and non-streaming generation,
        so the two response paths can't silently drift into different assistant
        behavior (they used to each hand-roll their own)."""
        history_section = ""
        if conversation_history:
            history_section = f"""
===== CONVERSATION HISTORY =====
{conversation_history}
===== END CONVERSATION HISTORY =====
"""
        return f"""You are Music-Assist, a professional LDS Church music expert.
{history_section}
RULES:
1. Use CONTEXT below as your only source.
2. If asked 'what is hymn X' or 'which hymn is number X', respond with ONLY the TITLE of the hymn in bold, nothing else.
3. For general questions, be direct - give specific numbers, names, and handbook sections.
4. Use Markdown (lists, bolding, tables) where it aids clarity.
5. Keep it thorough but under 150 words.

CONTEXT:
{context}

Question: {query}

Answer:"""

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

            # STEP 1: Load conversation history and detect whether this is a
            # context-dependent follow-up ("tell me more", "explain that further").
            # This has to happen *before* the cache lookup below: the response
            # cache is keyed only on query text, so a context-dependent query
            # can't be served from a cache entry that was generated for a
            # different user's different conversation.
            has_history = False
            last_question = ""
            if conversation_id:
                history = await asyncio.to_thread(self.memory.get_history, conversation_id)
                has_history = bool(history)
                if has_history:
                    # Get the very last question from the user in history
                    last_question = history[-1][0]

            is_pure_followup = has_history and len(query.split()) < 12 and any(
                w in query.lower() for w in
                ["more", "further", "simple", "it", "that", "why", "elaborate", "layman", "tell me", "explain"]
            )

            # STEP 0.5: Check cache for instant response (stateless queries only)
            cache_key = query.lower().strip()
            if not is_pure_followup and cache_key in self._response_cache:
                logger.info(f"⚡ Cache HIT for query: {query[:50]}...")
                cached_result = self._response_cache[cache_key].copy()
                cached_result["conversation_id"] = conversation_id or "cached"
                cached_result["metrics"]["response_time_ms"] = 0  # Instant!
                cached_result["metrics"]["cache_hit"] = True
                # Still save to conversation history
                if conversation_id and user_id:
                    await asyncio.to_thread(self.memory.add_message, conversation_id, query, cached_result["answer"], user_id)
                return cached_result

            logger.info(f"Processing query (conv_id={conversation_id}): {query[:100]}...")

            if not is_music_related_question(query, has_history=has_history):
                logger.info(f"Off-topic query detected: {query[:50]}")
                return {
                    "answer": "I appreciate your question, but I'm Music-Assist—specialized in Church of Jesus Christ of Latter-day Saints music topics. I can help with:\n\n• **Hymns** and sacred music\n• **Choir** organization and conducting\n• **Music callings** and responsibilities\n• **Music theory** and training\n• Church **music guidelines** and policies\n\nYour current question appears to be outside my expertise. Please feel free to ask me about Church music! I'm here to help. 🎵",
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
            
            # Auto-recovery: If not ready, try to load it again (maybe DB was just built)
            if not self._ready:
                await self.initialize()

            if not self._ready:
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
            
            # RE-WRITE QUERY FOR BETTER RETRIEVAL
            # If the user says "tell me more" or "into layman terms",
            # we combine it with the previous question so the database search knows what to look for.
            search_query = query
            if is_pure_followup:
                search_query = f"{last_question} {query}"
                logger.info(f"Augmented search query: {search_query}")

            # STEP 2: Try local vector store first
            search_start = time.time()
            local_docs = await self._search_local(search_query)
            metrics['local_docs_count'] = len(local_docs)
            metrics['search_time_ms'] = int((time.time() - search_start) * 1000)
            
            # STEP 3: Check if local results are sufficient
            needs_web_search = self._should_search_web(query, local_docs)
            
            web_results = []
            if needs_web_search:
                logger.info("Local data insufficient, searching Church websites...")
                web_start = time.time()
                web_results = await self.web_searcher.search(query)
                metrics['web_results_count'] = len(web_results)
                metrics['search_time_ms'] += int((time.time() - web_start) * 1000)
                logger.info(f"Found {len(web_results)} web results")

            # STEP 4: Combine local + web context
            combined_context = self._combine_contexts(local_docs, web_results)

            # STEP 4.5: Calculate confidence level for this query
            confidence_level = self._calculate_confidence(local_docs, web_results, query)

            # STEP 5: Generate answer with combined context
            gen_start = time.time()
            result = await self._generate_answer(query, combined_context, conversation_history_str)
            metrics['generation_time_ms'] = int((time.time() - gen_start) * 1000)

            # Estimate tokens and cost
            input_text = combined_context + query + conversation_history_str
            output_text = result
            metrics['input_tokens_estimated'] = int(len(input_text.split()) * 1.3)
            metrics['output_tokens_estimated'] = int(len(output_text.split()) * 1.3)
            
            # Calculate cost
            input_cost = (metrics['input_tokens_estimated'] / 1000) * settings.cost_per_1k_input_tokens
            output_cost = (metrics['output_tokens_estimated'] / 1000) * settings.cost_per_1k_output_tokens
            metrics['cost_usd'] = round(input_cost + output_cost, 6)
            
            # Update global cost tracking
            self.total_input_tokens += metrics['input_tokens_estimated']
            self.total_output_tokens += metrics['output_tokens_estimated']
            
            # Determine search method
            search_method = "hybrid (local + web)" if web_results else "local only"

            # 📦 Store in cache for instant repeat query
            final_result = {
                "answer": result,
                "sources": self._extract_sources(local_docs, web_results),
                "search_method": search_method,
                "confidence": confidence_level,
                "music_context": music_context,
                "metrics": {
                    "response_time_ms": int((time.time() - start_time) * 1000),
                    "search_time_ms": metrics['search_time_ms'],
                    "generation_time_ms": metrics['generation_time_ms'],
                    "local_chunks_retrieved": metrics['local_docs_count'],
                    "web_results_retrieved": metrics['web_results_count'],
                    "input_tokens_estimated": metrics['input_tokens_estimated'],
                    "output_tokens_estimated": metrics['output_tokens_estimated'],
                    "cost_usd": metrics['cost_usd'],
                    "confidence_level": confidence_level,
                    "conversation_length": len(conversation_history_str.split('\n\n')) if conversation_history_str else 1,
                    "timestamp": datetime.utcnow().isoformat(),
                    "cache_hit": False
                }
            }
            
            # Cache only stateless/context-free answers - a follow-up's answer is
            # only valid for the conversation it was generated in, so it must
            # never be served back out to a different conversation via the cache.
            if not is_pure_followup:
                if len(self._response_cache) >= self._cache_max_size:
                    # Remove first key (simple FIFO)
                    self._response_cache.pop(next(iter(self._response_cache)))
                self._response_cache[cache_key] = final_result

            # Update conversation history in SQLite (Background thread)
            await asyncio.to_thread(self.memory.add_message, conversation_id, query, result, user_id)
            
            # Return result with the provided conversation_id
            response_to_return = final_result.copy()
            response_to_return["conversation_id"] = conversation_id
            return response_to_return
            
        except ValueError as e:
            # Input validation errors
            self.failed_queries += 1
            logger.warning(f"Invalid input: {e}")
            raise
        except Exception as e:
            self.failed_queries += 1
            logger.error(f"Error processing query: {e}", exc_info=True)
            raise

    async def stream_query(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """
        Streaming version of current RAG pipeline query.
        Yields JSON chunks for metadata and content deltas.
        """
        try:
            # 1. Validation
            query = self._validate_and_sanitize_input(query)
            self.total_queries += 1

            # 2. History check for topic guidance
            has_history = False
            last_question = ""
            if conversation_id:
                history = await asyncio.to_thread(self.memory.get_history, conversation_id)
                has_history = bool(history)
                if has_history:
                    last_question = history[-1][0]

            if not is_music_related_question(query, has_history=has_history):
                 off_topic_msg = "I appreciate your question, but I'm Music-Assist—specialized in Church of Jesus Christ of Latter-day Saints music topics. I can help with:\n\n• **Hymns** and sacred music\n• **Choir** organization and conducting\n• **Music callings** and responsibilities\n• **Music theory** and training\n• Church **music guidelines** and policies\n\nYour current question appears to be outside my expertise. Please feel free to ask me about Church music! I'm here to help. 🎵"
                 yield json.dumps({"type": "content", "delta": off_topic_msg})
                 return

            # 3. Retrieval
            if not self._ready:
                await self.initialize()
            
            search_query = query
            if has_history and len(query.split()) < 8: # Simple follow-up
                search_query = f"{last_question} {query}"

            local_docs = await self._search_local(search_query)
            needs_web_search = self._should_search_web(query, local_docs)
            
            web_results = []
            if needs_web_search:
                web_results = await self.web_searcher.search(query)
            
            combined_context = self._combine_contexts(local_docs, web_results)
            sources = self._extract_sources(local_docs, web_results)
            confidence = self._calculate_confidence(local_docs, web_results, query)
            
            # Emit metadata chunk (sources, confidence)
            yield json.dumps({
                "type": "metadata",
                "sources": sources,
                "confidence": confidence,
                "conversation_id": conversation_id or f"conv_{int(time.time())}"
            })

            # 4. Generate & Stream
            conv_history = await self._get_formatted_conversation_history(conversation_id)
            prompt = self._build_prompt(query, combined_context, conv_history)

            full_answer = ""
            async for chunk in self.llm.astream(prompt):
                delta = chunk.content
                full_answer += delta
                yield json.dumps({"type": "content", "delta": delta})

            # 5. Persist
            final_cid = conversation_id or f"conv_{int(time.time())}"
            await asyncio.to_thread(self.memory.add_message, final_cid, query, full_answer, user_id)

        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield json.dumps({"type": "error", "message": str(e)})

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
            
            # Save vector store (blocking disk I/O - offload so it doesn't stall the event loop)
            await asyncio.to_thread(self.vector_store.save_local, self.vector_db_path)

            abs_path = os.path.abspath(self.vector_db_path)
            logger.info(f"Added {len(documents)} documents ({len(splits)} chunks)")
            logger.info(f"Saved vector store to: {abs_path}")

            self._ready = True
            
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
            # Directory scanning + file reads are blocking disk I/O; run them off
            # the event loop instead of stalling every other in-flight request.
            documents = await asyncio.to_thread(self._load_documents_from_disk)

            if not documents:
                raise ValueError("No documents found to index")

            # Rebuild vector store
            await self.add_documents(documents)

            return {"status": "success", "documents_indexed": len(documents)}

        except Exception as e:
            logger.error(f"Error rebuilding vector store: {e}", exc_info=True)
            raise

    def _load_documents_from_disk(self) -> List[Dict]:
        """Read every crawled/structured JSON doc into {content, metadata} dicts.

        Synchronous by design - callers must run this via asyncio.to_thread.
        """
        data_dirs = ["./data/crawled", "./data/structured", "./data/music_theory"]
        documents = []

        for d in data_dirs:
            if not os.path.exists(d):
                logger.warning(f"Directory not found during rebuild: {d}")
                continue

            logger.info(f"Processing files from {d}...")
            for filename in os.listdir(d):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(d, filename), 'r', encoding='utf-8') as f:
                            data = json.load(f)

                            # Extract content based on format (structured vs crawled)
                            content = ""
                            metadata = {"source_file": filename, "directory": d}

                            if "searchable_content" in data:
                                # Structured hymn metadata
                                content = data["searchable_content"]
                                metadata.update({
                                    "title": data.get("title", ""),
                                    "number": data.get("number", 0),
                                    "type": "hymn_metadata"
                                })
                            elif "content" in data:
                                # Standard crawled document
                                content = data["content"]
                                metadata.update({
                                    "source": data.get("url", ""),
                                    "title": data.get("title", ""),
                                    "timestamp": data.get("timestamp", "")
                                })

                            if content and len(content) > 10:
                                documents.append({
                                    "content": content,
                                    "metadata": metadata
                                })
                    except Exception as file_error:
                        logger.error(f"Error reading file {filename} in {d}: {file_error}")

        return documents
    
    async def get_stats(self) -> Dict:
        """Get comprehensive pipeline statistics for monitoring."""
        try:
            # Calculate total cost
            total_input_cost = (self.total_input_tokens / 1000) * settings.cost_per_1k_input_tokens
            total_output_cost = (self.total_output_tokens / 1000) * settings.cost_per_1k_output_tokens
            total_cost = total_input_cost + total_output_cost

            stats = {
                "status": "healthy" if self.vector_store is not None else "degraded",
                "vector_store_exists": self.vector_store is not None,
                "active_conversations_in_session": len(self._local_conversations),
                "model": self.model_name,
                "configuration": {
                    "chunk_size": self.chunk_size,
                    "chunk_overlap": self.chunk_overlap,
                    "max_tokens": settings.max_tokens,
                    "temperature": settings.temperature
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
            retriever = self._build_retriever()

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
        Balanced web search logic.
        """
        # 1. No local docs → search web
        if not local_docs:
            return True
        
        # 2. Local docs are too brief or placeholder → search web for more detail
        avg_length = sum(len(doc.page_content) for doc in local_docs) / len(local_docs)
        
        # Detect if the local docs are just small metadata snippets (which are fine) vs generic placeholders
        is_metadata = any(doc.metadata.get('type') == 'hymn_metadata' for doc in local_docs)
        
        if not is_metadata and avg_length < settings.min_content_length_for_local:
            return True

        # 3. Person specific queries often need web data for biographies
        query_lower = query.lower()
        if any(ind in query_lower for ind in ['who is', 'biography', 'composer', 'arranger']):
            # Only skip if we have very high quality local biography (unlikely)
            if avg_length < 1500:
                return True
                
        # 4. Explicit requests for web search
        if "google" in query_lower or "online" in query_lower or "latest" in query_lower:
            return True

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
            if avg_length > settings.min_content_length_for_local:
                return "high"
        
        # Medium confidence: Some local sources, or good web results
        if len(local_docs) >= 1 or len(web_results) >= 2:
            # Factual queries with web fallback are medium confidence
            if is_factual_query and web_results:
                return "medium"
            return "medium" if web_results else "high"
        
        # Low confidence: Very few sources
        return "low"
    
    def _combine_contexts(self, local_docs: List[Document], web_results: List[Dict]) -> str:
        """
        Combine local vector store results with web search results
        
        Returns: Formatted context string for LLM
        """
        # Context length management to prevent token overflow
        MAX_CONTEXT_LENGTH = settings.max_context_length
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
        max_retries = settings.max_retries
        retry_delay = settings.retry_base_delay
        
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
                
                prompt = self._build_prompt(query, context, conversation_history)

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