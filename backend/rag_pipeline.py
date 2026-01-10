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


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline for Music-Assist
    """
    
    def __init__(
        self,
        vector_db_path: str = "./data/vector_store",
        model_name: str = "gpt-3.5-turbo",
        chunk_size: int = 1000,
        chunk_overlap: int = 200
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
            temperature=0.3,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        self.vector_store = None
        self.qa_chain = None
        self.conversations = {}
        
    async def initialize(self):
        """Initialize or load vector store"""
        try:
            # Try to load existing vector store - check for actual index file
            index_file = os.path.join(self.vector_db_path, "index.faiss")
            if os.path.exists(index_file):
                self.vector_store = FAISS.load_local(
                    self.vector_db_path,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                print(f"✓ Loaded existing vector store from {self.vector_db_path}")
            else:
                print("! No existing vector store found. Please run crawler first.")
                # Create empty vector store as fallback
                try:
                    self.vector_store = FAISS.from_texts(
                        ["Initial placeholder document"],
                        self.embeddings,
                        metadatas=[{"source": "system", "type": "placeholder"}]
                    )
                except Exception as e:
                    print(f"⚠ Could not create placeholder vector store: {e}")
                    print("  Server will start in limited mode until crawler is run")
                    self.vector_store = None
                
            # Initialize QA chain (if vector store available)
            if self.vector_store:
                self._initialize_qa_chain()
            
        except Exception as e:
            print(f"Error initializing RAG pipeline: {e}")
            raise
    
    def _initialize_qa_chain(self):
        """Initialize the conversational QA chain using LCEL"""
        
        # Create retriever
        retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4}
        )
        
        # Custom prompt template for music theory context
        qa_system_prompt = """You are Music-Assist, a helpful assistant specializing in music theory as it applies to hymns and choir music of The Church of Jesus Christ of Latter-day Saints.

Use the following pieces of context to answer the question. If you don't know the answer based on the context, say so honestly. Always provide beginner-friendly explanations.

Context:
{context}

Question: {question}

Helpful Answer (be clear, accurate, and beginner-friendly):"""

        qa_prompt = PromptTemplate(
            template=qa_system_prompt,
            input_variables=["context", "question"]
        )
        
        # Format documents for context
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)
        
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
        Process a user query through the RAG pipeline
        """
        try:
            if self.qa_chain is None:
                return {
                    "answer": "Vector store not initialized. Please run the crawler first to populate the knowledge base.",
                    "sources": [],
                    "conversation_id": conversation_id or "none"
                }
            
            # Generate conversation ID if not provided
            if not conversation_id:
                conversation_id = f"conv_{datetime.utcnow().timestamp()}"
            
            # Get or create conversation history
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = []
            
            # Query the chain
            result = await asyncio.to_thread(
                self.qa_chain.invoke,
                query
            )
            
            # Update conversation history
            self.conversations[conversation_id].append((query, result))
            
            # Keep only last 10 exchanges to manage memory
            if len(self.conversations[conversation_id]) > 10:
                self.conversations[conversation_id] = self.conversations[conversation_id][-10:]
            
            return {
                "answer": result,
                "sources": [],
                "conversation_id": conversation_id
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
            
            print(f"✓ Added {len(documents)} documents ({len(splits)} chunks)")
            
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