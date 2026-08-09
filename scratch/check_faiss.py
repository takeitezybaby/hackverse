import sys
sys.path.insert(0, '.')
try:
    import faiss
    idx = faiss.IndexFlatL2(4)
    print(f"faiss installed. IndexFlatL2 ntotal={idx.ntotal}")
except ImportError as e:
    print(f"faiss NOT installed: {e}")
