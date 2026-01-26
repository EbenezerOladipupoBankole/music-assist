
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

# Try common "missing char" fixes
for c1 in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/":
    for c2 in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/":
        # Insert 2 chars at the end before ==
        test_body = body[:-2] + c1 + c2 + "=="
        if len(test_body) % 4 == 0:
            new_key = header + test_body + footer
            d = data.copy()
            d['private_key'] = new_key
            
            try:
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf:
                    json.dump(d, tf)
                    tname = tf.name
                service_account.Credentials.from_service_account_file(tname)
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(d, f, indent=4)
                print(f"✅ FIXED! Added {c1}{c2}")
                os.unlink(tname)
                exit(0)
            except:
                if os.path.exists(tname): os.unlink(tname)

print("💀 Failed to fix padding.")
