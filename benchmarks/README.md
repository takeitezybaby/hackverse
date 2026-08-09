# 📊 Campus Buddy RAG Benchmark Metrics (Post-Strategy 4 Tuning)

### 🔬 Testing Methodology & Active Optimization
> **Evaluated RAG performance across 20 synthetic campus queries measuring Context Precision, Factual Groundedness, and Out-of-Domain Guardrail Precision using an automated RAGAS-style evaluation framework.**

- **Active Strategy**: **Strategy 4 — Strict Out-of-Domain Prompt Scope Refinement** (`_GUARDRAIL` in `app/llm/prompts.py`).

---

### 🏆 Benchmark Results Overview

| Evaluation Metric | Baseline Score | Post-Strategy 4 Score | Metric Definition & RAGAS Alignment |
| :--- | :---: | :---: | :--- |
| **Context Retrieval Precision@5** | 90.0% | **95.0%** (19/20) | FAISS top-5 vector search returns exact ground-truth venue context. |
| **Intent Routing Precision** | 90.0% | **95.0%** (19/20) | Query intent classifier accuracy across Schedule, Rec, Peak, and Timing intents. |
| **Factual Groundedness Score** | 75.0% | **95.0%** (19/20) | Zero-hallucination rate of quoted figures against context evidence. |
| **Out-of-Domain Guardrail Precision** | 50.0% | **100.0%** (4/4) | Intercepts non-campus queries (*railway stations, recipes, flights*) before LLM inference. |
| **Overall RAG Benchmark Accuracy** | 75.0% | **95.0%** (19/20) | **End-to-End System Accuracy across all 20 benchmark test cases.** |

---

### 📂 File Locations
- JSON Data: [`rag_benchmark_results.json`](file:///c:/Users/yash3/Desktop/hackverse/benchmarks/rag_benchmark_results.json)
- Prompt Configurations: [`app/llm/prompts.py`](file:///c:/Users/yash3/Desktop/hackverse/app/llm/prompts.py)
