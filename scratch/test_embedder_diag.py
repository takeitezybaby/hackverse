import urllib.request
import json
import time
import sys

host = 'http://127.0.0.1:11434'
models = ['granite-embedding:278m', 'nomic-embed-text:latest', 'bge-m3:latest']

print("=== Ollama Embedding Diagnostic ===")
print("1. Checking available models via GET /api/tags...")
try:
    req = urllib.request.Request(f"{host}/api/tags")
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode())
        available = [m['name'] for m in data.get('models', [])]
        print("   Available models:", available)
except Exception as e:
    print("   Failed /api/tags:", e)
    sys.exit(1)

for model_name in models:
    print(f"\n2. Testing model '{model_name}' on /api/embed (timeout=30s)...")
    t0 = time.time()
    try:
        payload = json.dumps({"model": model_name, "input": ["Hello world"]}).encode('utf-8')
        req = urllib.request.Request(f"{host}/api/embed", data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            embeddings = data.get("embeddings", [])
            dim = len(embeddings[0]) if embeddings else 0
            elapsed = time.time() - t0
            print(f"   SUCCESS! Embedded 1 text in {elapsed:.2f}s. Vector dimension: {dim}")
    except Exception as e:
        elapsed = time.time() - t0
        print(f"   FAILED in {elapsed:.2f}s: [{type(e).__name__}] {e}")
