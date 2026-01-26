
import os
import re

file_path = r'c:\Users\LENOVO\music-assist\backend\firebase-key.json'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to find backslash followed by any non-standard escape char in the private_key field
# We know the key is roughly in the middle. 
# Let's just fix the most likely culprits: \q, \e, \v etc that should be \n
fixed_content = content.replace('\\q', '\\n').replace('\\e', '\\n').replace('\\v', '\\n')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print("✅ Attempted to fix invalid escapes in firebase-key.json")

# Verify
try:
    import json
    with open(file_path, 'r', encoding='utf-8') as f:
        json.load(f)
    print("✅ JSON is now VALID!")
except Exception as e:
    print(f"❌ JSON is still INVALID: {e}")
