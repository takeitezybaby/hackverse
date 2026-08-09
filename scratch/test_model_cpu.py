import urllib.request, json

# Try CPU-only mode (num_gpu=0) to rule out VRAM issue
print("Testing granite3.1-dense:8b with CPU-only (num_gpu=0)...")
payload = json.dumps({
    'model': 'granite3.1-dense:8b',
    'prompt': 'Reply with just the word OK.',
    'stream': False,
    'options': {'num_predict': 5, 'temperature': 0.0, 'num_gpu': 0}
}).encode()
req = urllib.request.Request(
    'http://127.0.0.1:11434/api/generate',
    data=payload,
    headers={'Content-Type': 'application/json'}
)
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.loads(r.read())
        print("Response:", resp.get('response', '').strip())
        print("Done reason:", resp.get('done_reason'))
except Exception as e:
    print("Error:", type(e).__name__, e)
