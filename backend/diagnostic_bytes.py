
with open(r'c:\Users\LENOVO\music-assist\backend\firebase-key.json', 'rb') as f:
    data = f.read()
    
# Find \e or suspicious characters
print(f"File length: {len(data)}")

# Search for backslash followed by anything other than n, r, t, ", /
for i in range(len(data)-1):
    if data[i] == ord('\\'):
        next_char = chr(data[i+1])
        if next_char not in ['n', 'r', 't', '"', '/', 'u', '\\']:
            print(f"🚨 Found suspicious escape: \\{next_char} at byte {i}")
            # Print context
            start = max(0, i - 10)
            end = min(len(data), i + 10)
            print(f"Context: {data[start:end]}")

try:
    import json
    json.loads(data.decode('utf-8'))
    print("✅ JSON is actually valid when decoded as utf-8")
except Exception as e:
    print(f"❌ JSON error: {e}")
