"""
Interactive Terminal Chat for Music-Assist RAG
Chat with the RAG pipeline directly through the terminal
"""
import asyncio
import sys
import os
from datetime import datetime
from rag_pipeline import RAGPipeline
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class TerminalChat:
    def __init__(self):
        self.rag = None
        self.conversation_id = f"terminal_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    async def initialize(self):
        """Initialize RAG pipeline"""
        print("\n" + "="*70)
        print("🎵 MUSIC-ASSIST TERMINAL CHAT 🎵")
        print("="*70)
        print("Initializing RAG pipeline...")
        
        try:
            self.rag = RAGPipeline(
                vector_db_path=os.getenv("VECTOR_DB_PATH", "./data/vector_store"),
                model_name=os.getenv("LLM_MODEL", "gpt-3.5-turbo")
            )
            
            await self.rag.initialize()
            
            print("✅ RAG Pipeline initialized successfully!")
            print(f"📚 Vector store loaded")
            print("="*70)
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize RAG: {e}")
            return False
    
    def print_welcome(self):
        """Print welcome message"""
        print("\n💬 Welcome to Music-Assist Interactive Chat!")
        print("-"*70)
        print("Ask me anything about:")
        print("  • LDS Hymns and sacred music")
        print("  • Music theory (chords, scales, harmony)")
        print("  • Church music callings and guidelines")
        print("  • Composers and arrangers")
        print("\nCommands:")
        print("  • 'quit' or 'exit' - End the conversation")
        print("  • 'clear' - Start a new conversation")
        print("  • 'stats' - View usage statistics")
        print("-"*70 + "\n")
    
    async def chat_loop(self):
        """Main chat loop"""
        while True:
            try:
                # Get user input
                user_input = input("\n🎹 YOU: ").strip()
                
                # Handle commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Thanks for chatting! Goodbye!\n")
                    break
                
                if user_input.lower() == 'clear':
                    self.conversation_id = f"terminal_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    print("\n🔄 Conversation history cleared!\n")
                    continue
                
                if user_input.lower() == 'stats':
                    await self.show_stats()
                    continue
                
                if not user_input:
                    continue
                
                # Show thinking indicator
                print("\n🤔 Music-Assist is thinking...")
                
                # Get response from RAG
                start_time = asyncio.get_event_loop().time()
                
                result = await self.rag.query(
                    query=user_input,
                    conversation_id=self.conversation_id,
                    user_id="terminal_user"
                )
                
                elapsed = asyncio.get_event_loop().time() - start_time
                
                # Print response
                print(f"\n🎵 MUSIC-ASSIST:")
                print("-"*70)
                print(result["answer"])
                print("-"*70)
                
                # Print metadata
                print(f"⏱️  {elapsed:.2f}s | 📚 {len(result['sources'])} sources | 🔍 {result.get('search_method', 'N/A')}", end="")
                
                if 'metrics' in result and 'cost_usd' in result['metrics']:
                    print(f" | 💰 ${result['metrics']['cost_usd']:.4f}")
                else:
                    print()
                
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Goodbye!\n")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}\n")
                continue
    
    async def show_stats(self):
        """Show conversation statistics"""
        try:
            stats = await self.rag.get_stats()
            
            print("\n📊 STATISTICS")
            print("-"*70)
            print(f"Total queries: {stats.get('total_queries', 0)}")
            print(f"Total cost: ${stats.get('total_cost_usd', 0):.4f}")
            print(f"Avg response time: {stats.get('avg_response_time_ms', 0):.0f}ms")
            print(f"Active conversations: {stats.get('active_conversations', 0)}")
            print(f"Vector store: {stats.get('vector_store_status', 'unknown')}")
            print("-"*70)
            
        except Exception as e:
            print(f"\n❌ Error fetching stats: {e}\n")

async def main():
    """Main entry point"""
    chat = TerminalChat()
    
    # Initialize RAG
    if not await chat.initialize():
        sys.exit(1)
    
    # Show welcome message
    chat.print_welcome()
    
    # Start chat loop
    await chat.chat_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!\n")
        sys.exit(0)
