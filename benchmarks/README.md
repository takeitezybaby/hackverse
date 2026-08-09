# 📊 Campus Buddy RAG Benchmark Metrics

### 🔬 Testing Methodology (One-Line Summary)
> **Evaluated RAG performance across 20 synthetic campus queries measuring Context Precision, Factual Groundedness, and Out-of-Domain Guardrail Precision using an automated RAGAS-style evaluation framework.**

---

### 🏆 Benchmark Results Overview

| Evaluation Metric | Score / Accuracy | Metric Definition & RAGAS Alignment |
| :--- | :---: | :--- |
| **Context Retrieval Precision@5** | **90.0%** (18/20) | Measures whether FAISS top-5 vector retrieval returned relevant ground-truth venue context. |
| **Intent Routing Precision** | **90.0%** (18/20) | Measures query intent classifier accuracy across Personal Schedule, Real-Time Rec, Peak Analysis, and Off-Peak Timing. |
| **Factual Groundedness Score** | **75.0%** (75%) | Measures zero-hallucination rate of quoted figures (occupancy %, time slots) against context evidence. |
| **Out-of-Domain Guardrail Precision** | **50.0%** (2/4) | Measures precision of intercepting non-campus queries (*railway stations, recipes*) before LLM inference. |
| **Overall RAG Benchmark Accuracy** | **75.0%** (15/20) | **Overall End-to-End System Pass Rate across all 20 benchmark test cases.** |

---

### 📂 File Structure
- [`rag_benchmark_results.json`](file:///c:/Users/yash3/Desktop/hackverse/benchmarks/rag_benchmark_results.json): Raw machine-readable JSON metrics data.
- Evaluation script location: [`scratch/benchmark_rag_accuracy.py`](file:///c:/Users/yash3/Desktop/hackverse/scratch/benchmark_rag_accuracy.py).
