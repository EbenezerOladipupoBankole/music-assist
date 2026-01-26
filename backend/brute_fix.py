
import json
import base64
from google.oauth2 import service_account
import tempfile
import os

path = r'c:\Users\LENOVO\music-assist\backend\firebase-key.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

key = data['private_key']
header = "-----BEGIN PRIVATE KEY-----\n"
footer = "\n-----END PRIVATE KEY-----\n"

body = key.split(header)[1].split(footer.strip())[0].replace('\n', '').replace('\r', '')

variations = [
    body,                   # As is (1622)
    body[:-2],              # Remove == (1620)
    body + "==",            # Add more padding (1624)
    body[:-2] + "==",       # (1622 - no change)
]

print(f"Original body length: {len(body)}")

for i, v in enumerate(variations):
    if len(v) % 4 != 0:
        print(f"Variation {i} skipped (length {len(v)} not multiple of 4)")
        continue
        
    # Reconstruct PEM
    new_body = ""
    for j in range(0, len(v), 64):
        new_body += v[j:j+64] + "\n"
    new_key = header + new_body + "-----END PRIVATE KEY-----\n"
    
    test_data = data.copy()
    test_data['private_key'] = new_key
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf:
            json.dump(test_data, tf)
            tname = tf.name
        service_account.Credentials.from_service_account_file(tname)
        print(f"✅ Variation {i} WORKS! (Length {len(v)})")
        # Save this one!
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=4)
        os.unlink(tname)
        break
    except Exception as e:
        print(f"❌ Variation {i} fails: {e}")
        if os.path.exists(tname): os.unlink(tname)
else:
    print("💀 None of the variations worked.")
