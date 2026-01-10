import urllib.request
import json
import sys

# Configuration
API_URL = "http://127.0.0.1:8000/chat"

def chat():
    print("\n=== Music Assist Terminal Chat ===")
    print("Type 'quit' or 'exit' to stop.\n")
    
    conversation_id = None
    
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ['quit', 'exit']:
                print("Goodbye!")
                break
            
            if not user_input:
                continue

            # Prepare payload
            payload = {
                "message": user_input,
                "conversation_id": conversation_id
            }
            
            # Send request
            req = urllib.request.Request(
                API_URL, 
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
                response_text = data['response']
                print(f"Bot: {response_text}\n")
                
                if "Vector store not initialized" in response_text:
                    print("    [!] Tip: The database is empty.")
                    print("    1. Create a .env file with your OPENAI_API_KEY")
                    print("    2. Run: python populate_db.py")
                    print("    3. Restart the server\n")

                # Keep conversation ID for context if supported
                conversation_id = data.get('conversation_id')
                
        except urllib.error.HTTPError as e:
            print(f"\n[!] Server Error ({e.code}): {e.reason}")
            print(f"    Check the backend terminal for details (e.g., missing API Key).\n")
            
        except urllib.error.URLError:
            print("\n[!] Error: Could not connect to server.")
            print("    Make sure the backend is running on port 8000.\n")
            break
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\n[!] Error: {e}\n")

if __name__ == "__main__":
    chat()