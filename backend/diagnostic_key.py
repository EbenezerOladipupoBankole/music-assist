
path = r'c:\Users\LENOVO\music-assist\backend\firebase-key.json'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# The error message says "At line 1, column 1621" for the key loading part.
# Let's find the private_key value
import json
data = json.loads(text)
key = data['private_key']

print(f"Key length: {len(key)}")
# Look at the vicinity of 1620
start = max(0, 1620 - 40)
end = min(len(key), 1620 + 40)
print(f"Around 1620: {repr(key[start:end])}")

# Check for any backslashes in the key that aren't \n
for i, char in enumerate(key):
    if char == '\\':
        print(f"🚨 Backslash found at index {i}: {repr(key[i:i+5])}")

# Try to load it with the auth library to see exactly what fails
try:
    from google.oauth2 import service_account
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf:
        json.dump(data, tf)
        temp_name = tf.name
    service_account.Credentials.from_service_account_file(temp_name)
    print("✅ Credentials verified!")
    os.unlink(temp_name)
except Exception as e:
    print(f"❌ Credentials error: {e}")
