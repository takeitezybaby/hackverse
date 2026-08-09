import urllib.request, json

# Model sizes
with urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=5) as r:
    data = json.loads(r.read())
print("Available models:")
for m in data.get('models', []):
    size_gb = m.get('size', 0) / 1e9
    print(f"  {m['name']}: {size_gb:.1f} GB")

# Try generate with a simple prompt — no stream, short output
print("\nTesting granite3.1-dense:8b generate...")
payload = json.dumps({
    'model': 'granite3.1-dense:8b',
    'prompt': 'Reply with just the word OK.',
    'stream': False,
    'options': {'num_predict': 5, 'temperature': 0.0}
}).encode()
req = urllib.request.Request(
    'http://127.0.0.1:11434/api/generate',
    data=payload,
    headers={'Content-Type': 'application/json'}
)
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read())
        print("Response:", resp.get('response', '').strip())
        print("Done reason:", resp.get('done_reason'))
except Exception as e:
    print("Error:", type(e).__name__, e)
