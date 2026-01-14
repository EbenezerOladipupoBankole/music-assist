from firebase_functions import https_fn
from firebase_admin import initialize_app
import json
import os
import glob

initialize_app()

def load_knowledge_base():
    """Loads the crawled JSON documents from the data directory."""
    documents = []
    # Path is relative to the function root during execution
    data_path = os.path.join(os.path.dirname(__file__), "data", "crawled", "*.json")
    files = glob.glob(data_path)
    
    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                doc = json.load(f)
                documents.append(doc)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    return documents

def find_best_match(query, documents):
    """Simple keyword search to find relevant content."""
    query_lower = query.lower()
    best_doc = None
    max_score = 0

    for doc in documents:
        content = doc.get("content", "").lower()
        title = doc.get("title", "").lower()
        
        # Simple scoring: count occurrences of query terms
        score = content.count(query_lower) + (title.count(query_lower) * 2)
        
        if score > max_score:
            max_score = score
            best_doc = doc

    return best_doc

@https_fn.on_request(min_instances=0, max_instances=1)
def api(req: https_fn.Request) -> https_fn.Response:
    """
    Handles API requests from the frontend.
    Matches the rewrite rule in firebase.json: "function": "api"
    """
    
    # 1. Handle CORS (Cross-Origin Resource Sharing)
    # Allow requests from your Firebase domain
    headers = {
        'Access-Control-Allow-Origin': '*', # For production, change * to your specific domain
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json'
    }

    if req.method == 'OPTIONS':
        return https_fn.Response("", status=204, headers=headers)

    # 2. Parse the Request
    try:
        req_json = req.get_json()
        user_message = req_json.get('text', '') if req_json else ''
        
        if not user_message:
             # Fallback if text is in query params (for testing)
            user_message = req.args.get('text', '')

    except Exception:
        return https_fn.Response(json.dumps({"error": "Invalid JSON"}), status=400, headers=headers)

    # 3. Logic: Search the Knowledge Base
    documents = load_knowledge_base()
    match = find_best_match(user_message, documents)

    response_data = {
        "text": "I searched the sacred music archive but could not find a specific reference for that.",
        "sources": []
    }

    if match:
        # Construct a response based on the found document
        # In a real RAG system, you would send 'match['content']' to an LLM (like OpenAI) here.
        response_data["text"] = f"Based on the {match.get('title')}:\n\n{match.get('content')[:500]}..."
        response_data["sources"] = [{
            "title": match.get("title"),
            "url": match.get("url")
        }]

    # 4. Return Response
    return https_fn.Response(json.dumps(response_data), status=200, headers=headers)