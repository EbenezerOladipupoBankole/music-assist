
import json
import base64
from google.oauth2 import service_account
import tempfile
import os

key_body = (
    "MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCEqcAOkLP2JPBO"
    "X49FJhdFrshvR53jHTVUI3nMqLO8W+RUnrRcSW8OvhjdE8gqXeLEko1v4m5zhtHc"
    "D3HsEWTSxFpG52+2VYu9/O/ItgQGEcTl6z0rHvhU8wM9ufMtwTjfvgRX5WQ3Fezo"
    "ipb7nS1c0i0tsEdsiGQMCevYj8QtMLAfIiQnkOfTummFvdB6b2PHiw2ole1czwc7"
    "13iRtv0L3ZAa1uuAH27SYi4qIUhau9wnUcGydrXl3iV2wAF/xgdEk9bNHDZQXgZO"
    "6O8zAsA+LzUq0Yy8JOtPSEGuGbj+AEEEHxL32g1qxGFZ8K1W5cxMMGmpgtZJxejO"
    "SvyDuuH9AgMBAAECggEAA1qrYXLlKe8LKGAgJjZtVjSyGqYr5schRwxSkwsc6EFG"
    "h6EvnDm7FhtWU5ihcfjHuAKgktidxEv/WFoHnllePDn8slg9qdWF3/raMS/w8BpY"
    "6RtGg6WXz8YJKfFepaSCBJ4wS+yf2Qiz4blHUftKX1NtEv+m/qaAKRHDJcmUwzOz"
    "npZ3W9SGgsWoXQU37UbRFVJ+RIHlkUdKVs6EaqVBAYerGbrgwdoVfvqMJ2XFPxur"
    "+ToGneGzuW1O7OFteJG9DysnQIdwWNTxnEqEVVOVlE4IM9Qel7Ak0pp0SnApFX5t"
    "XGUEj85Ncn486zzXqZi8kkkUvCWZ021B2ttlnpONfQKBgQC5OT9tTqpYx8Yx5G4s"
    "cVBUfHkODVbgOBMiMPZGSgsJx85Z+G49RQaRwivwYLVJvdS6KuQLEghDnWR823u"
    "PfI46toZEahzICxIZr13RZ/L66QNhaxM3EQRmeBrggCN5ulqORJwDxocvGCMReeL"
    "mhGUo27cc0U6EIjUhvq1ZkYm6wKBgQC3Wvr6eINR0f3t/DgqJnMUEdv3sO5itfLO"
    "JqlzGvvxrhoqmysyHxN2/L40ad3ZMDoYUuNl6aDQnIpbP0mtmWTvbVBPUQ1Zx7XE"
    "g5K62SkIbI8X6HS/+0PNsm1qMjVcRfogDUUIv9RLZugr/G9E5Rc+JQZMmOlqAhIV"
    "9drxEJswtwKBgFas3217PmPFOI3oY1YrK89hVVyCoRVsvYmTBnL1PsNKm2X1or82"
    "kG2rh/kXCO5OCbaWgpI45pfxeDsQOwUdn9farqzEgps9FvvaeBb0Uc7POjnJr9NX"
    "z9Kcu1QTxcaho+C9TE98AbAoxtVdcPj24/s2b45hsqd1TVKGx5NThMh5AoGAajxY"
    "ts8kpz+YdU9x61ojyzkdzkHBnYf2iuNzwrGb0MgjeRQ2zu+ag5KlUhEU7UY4IufD"
    "cS/3J8Wuw/MTL1X8jHQGmTH64D/HEFvvrscPzlHH38cRi/7dS8wnhtBN5mD9xY5"
    "LXyYMKgLVZEJl011Thh9sdvXQgi5Geg9VvdcM7kCgYA6N8qUVUo5HrxCmO5YBtcb"
    "zbySe9/qVSnfvxluw3oO9V/p0602ZSQXtruwX53EFWAcdwoTvNHEV39MN98zxj5I"
    "ERUE+tE6Ek2IplL3vkB8xLDTPVsAvQaR7ioZIH9fzvAAIJASiOxmmlAg1AGEbTJv"
    "atqfaqJeL2frvZ58NbB8Gw=="
)

header = "-----BEGIN PRIVATE KEY-----\n"
footer = "\n-----END PRIVATE KEY-----\n"
full_key = header
for i in range(0, len(key_body), 64):
    full_key += key_body[i:i+64] + "\n"
full_key += "-----END PRIVATE KEY-----\n"

path = r'c:\Users\LENOVO\music-assist\backend\firebase-key.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

data['private_key'] = full_key

with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4)

print("✅ KEY RESTORED FROM CLEAN SOURCE!")
try:
    service_account.Credentials.from_service_account_file(path)
    print("🚀 VALIDATED BY GOOGLE AUTH!")
except Exception as e:
    print(f"❌ Error during validation: {e}")
