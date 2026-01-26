
import json
import base64

path = r'c:\Users\LENOVO\music-assist\backend\firebase-key.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

key = data['private_key']
header = "-----BEGIN PRIVATE KEY-----\n"
footer = "\n-----END PRIVATE KEY-----\n"

if header in key and footer in key:
    body = key.split(header)[1].split(footer.strip())[0].replace('\n', '').replace('\r', '')
    print(f"Body length: {len(body)}")
    print(f"Body % 4: {len(body) % 4}")
    
    try:
        decoded = base64.b64decode(body)
        print(f"✅ Successful base64 decode! Byte length: {len(decoded)}")
    except Exception as e:
        print(f"❌ Base64 decode failed: {e}")
else:
    print("❌ Header/Footer not found")
