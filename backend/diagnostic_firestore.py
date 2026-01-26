
import firebase_admin
from firebase_admin import credentials, firestore
import os

def check_firestore():
    print("🔍 Diagnostic: Checking Firestore Data...")
    
    cred_path = r"c:\Users\LENOVO\music-assist\backend\firebase-key.json"
    if not os.path.exists(cred_path):
        print(f"❌ Error: {cred_path} not found")
        return

    try:
        # Use full path to avoid any confusion or escape issues
        cred = credentials.Certificate(cred_path)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        
        # 1. Total count
        print("\n--- Collections Info ---")
        convs_ref = db.collection('conversations')
        
        all_convs = list(convs_ref.limit(20).stream())
        print(f"Total conversations (sample of 20): {len(all_convs)}")
        
        for doc in all_convs:
            data = doc.to_dict()
            print(f"Session ID: {doc.id}")
            print(f"  Title: {data.get('title', 'N/A')}")
            print(f"  User: {data.get('user_id', 'ANONYMOUS')}")
            print(f"  Update: {data.get('last_updated')}")
            
            # Count messages
            msgs = list(doc.reference.collection('messages').limit(5).stream())
            print(f"  Messages in subcollection: {len(msgs)}")
            print("-" * 15)

    except Exception as e:
        import traceback
        print(f"❌ Firestore Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    check_firestore()
