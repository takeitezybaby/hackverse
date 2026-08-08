import time, sys, os
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

print("===================================================")
print("   Campus Twin Copilot -- Pre-Demo Model Warmup")
print("===================================================")

t0 = time.time()

try:
    from app.rag import CampusRAG
    rag = CampusRAG()
    print("1. Checking RAG Retriever & FAISS Index...")
    num_vecs = rag.seed_from_snapshots()
    print(f"   [OK] FAISS Index Loaded ({num_vecs} snapshot vectors)")

    print("\n2. Executing Throwaway Warmup Query to Ollama Granite...")
    warmup_start = time.time()
    
    # Connection retry loop (up to 5 attempts to handle daemon race conditions)
    res = None
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            res = rag.answer_question("Is Gymnasium busy right now?")
            if not res.get("is_fallback"):
                print(f"   [OK] Ollama connected on attempt {attempt}/{max_retries}!")
                break
        except Exception:
            pass
        if attempt < max_retries:
            print(f"   [WAIT] Ollama daemon initializing... retrying attempt {attempt}/{max_retries} in 1.5s")
            time.sleep(1.5)

    if res is None:
        res = rag.answer_question("Is Gymnasium busy right now?")

    warmup_time = (time.time() - warmup_start) * 1000

    print(f"   [OK] Model Response Generated in {warmup_time:.1f} ms")
    print(f"   [OK] Sample Response: {res['answer'][:120]}...")

    if res.get("is_fallback"):
        print("\n[WARNING] Local Ollama daemon unreachable. System is running in Fallback mode.")
        print("   To run with full local LLM: `ollama serve` and `ollama pull granite3.1-dense:8b`")
    else:
        print("\n[SUCCESS] Ollama Granite model is fully warmed up and primed in GPU/VRAM!")

except Exception as e:
    print(f"\n[ERROR] Error during model warmup: {e}")

total_elapsed = time.time() - t0
print(f"\nWarmup complete in {total_elapsed:.2f}s.")
print("===================================================")
