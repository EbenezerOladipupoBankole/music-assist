
import os
import re

path = r'c:\Users\LENOVO\music-assist\backend\firebase-key.json'
with open(path, 'rb') as f:
    data = f.read()

# We look for a backslash followed by a character that's not a valid JSON escape char.
# Valid in JSON: " \ / b f n r t uXXXX
valid_escapes = b'\\"\\/bfnrtu'

new_data = bytearray()
i = 0
while i < len(data):
    if data[i] == ord('\\'):
        if i + 1 < len(data) and data[i+1] in valid_escapes:
            # Keep it
            new_data.append(data[i])
            i += 1
        else:
            # Skip the backslash!
            print(f"Skipping invalid backslash at byte {i}")
            i += 1
            continue
    new_data.append(data[i])
    i += 1

with open(path, 'wb') as f:
    f.write(new_data)

print("✅ Removed all invalid backslashes.")

# Final check
try:
    import json
    with open(path, 'r', encoding='utf-8') as f:
        d = json.load(f)
    print("✅ JSON is VALID!")
    # Normalize the key one last time
    key = d['private_key']
    header = "-----BEGIN PRIVATE KEY-----\n"
    footer = "\n-----END PRIVATE KEY-----\n"
    if header in key and footer in key:
        body = key.split(header)[1].split(footer.strip())[0].replace('\n', '').replace('\r', '').replace(' ', '')
        new_body = ""
        for j in range(0, len(body), 64):
            new_body += body[j:j+64] + "\n"
        d['private_key'] = header + new_body + "-----END PRIVATE KEY-----\n"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(d, f, indent=4)
        print("✅ Key normalized.")
    
    # Try loading with google-auth
    from google.oauth2 import service_account
    service_account.Credentials.from_service_account_file(path)
    print("🚀 FIREBASE KEY IS FULLY FUNCTIONAL!")
except Exception as e:
    print(f"❌ Still failed: {e}")
