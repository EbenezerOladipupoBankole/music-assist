
import os
import re

file_path = r'c:\Users\LENOVO\music-assist\backend\firebase-key.json'
with open(file_path, 'r', encoding='utf-8') as f:
    # Read the file as it is now
    content = f.read()

# We need to find everywhere we put a \n that shouldn't be there.
# But wait, we already reconstructed the key, so we lost the positions!
# UNLESS we can find characters that look like they were meant to be part of the base64.

# Actually, I'll try to just remove ALL newlines and see if I can find the "lost" characters.
# But wait, if I changed \q to \n, I lose the 'q'!

# I'll try to see if I can find a version of the file from BEFORE my fix.
# Since I'm on a system with git, maybe I can git checkout?
# No, it's not in git.

# Wait!
# I can try all 26 letters for the "suspicious" newline.
# There were only a few suspicious escapes.

import json
data = json.loads(content)
key = data['private_key']
header = "-----BEGIN PRIVATE KEY-----\n"
footer = "\n-----END PRIVATE KEY-----\n"
body = key.split(header)[1].split(footer.strip())[0].replace('\n', '').replace('\r', '')

print(f"Current body length: {len(body)}")
# If it's 1622, and it should be 1624, we are missing 2 characters.

import base64
from google.oauth2 import service_account
import tempfile

def try_key(b):
    new_body = ""
    for j in range(0, len(b), 64):
        new_body += b[j:j+64] + "\n"
    new_key = header + new_body + "-----END PRIVATE KEY-----\n"
    d = data.copy()
    d['private_key'] = new_key
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf:
        json.dump(d, tf)
        tname = tf.name
    try:
        service_account.Credentials.from_service_account_file(tname)
        os.unlink(tname)
        return new_key
    except:
        os.unlink(tname)
        return None

# Let's try to find where we have a newline that might have been a character.
# Wait! I know exactly where I put the newlines in my first fix!
# Around 1620.
# 'zxj5I' + ? + 'RUE'
# Let's try 'zxj5IERUE' (Wait, R was there, E was the escape?)

candidates = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/"

# Try replacing the newline at 1620 (or whatever it is now) with each candidate
for c in candidates:
    # Try inserting c at several positions near the end
    for pos in range(len(body)-10, len(body)):
        test_body = body[:pos] + c + body[pos:]
        if len(test_body) % 4 == 0:
            res = try_key(test_body)
            if res:
                print(f"🎯 FOUND IT! Char '{c}' at position {pos}")
                data['private_key'] = res
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
                exit(0)

print("💀 Brute force failed. Trying 2 character insertions...")
# This will be slow, but let's try a few.
