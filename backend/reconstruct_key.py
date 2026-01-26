
import json

path = r'c:\Users\LENOVO\music-assist\backend\firebase-key.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

key = data['private_key']
print("Searching for backslashes in the loaded key string...")
# Note: when json.load reads \n, it becomes a literal newline character in Python.
# If there were invalid escapes that I "fixed" to \n, they are now newlines.

for i, char in enumerate(key):
    if char == '\n':
        # Show context around newline
        start = max(0, i - 10)
        end = min(len(key), i + 10)
        print(f"Newline at index {i}. Context: {repr(key[start:end])}")

# Let's try to RECONSTRUCT the key by removing all newlines and then re-adding them every 64 chars
# (after the BEGIN header and before the END footer)

header = "-----BEGIN PRIVATE KEY-----\n"
footer = "\n-----END PRIVATE KEY-----\n"

if key.startswith(header) and key.strip().endswith(footer.strip()):
    body = key[len(header):-len(footer)].replace('\n', '').replace('\r', '')
    # Now body should be pure base64.
    # Check if it has any weird chars
    import re
    invalid_chars = re.findall(r'[^a-zA-Z0-9+/=]', body)
    if invalid_chars:
        print(f"🚨 Found invalid base64 characters in body: {invalid_chars}")
        # Clean them
        body = re.sub(r'[^a-zA-Z0-9+/=]', '', body)
    
    # Reconstruct with proper newlines
    new_body = ""
    for i in range(0, len(body), 64):
        new_body += body[i:i+64] + "\n"
    
    new_key = header + new_body + "-----END PRIVATE KEY-----\n"
    
    data['private_key'] = new_key
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print("✅ Key reconstructed and saved!")
else:
    print("❌ Key format not recognized as standard PEM")
