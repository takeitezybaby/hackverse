# 📊 Campus Buddy System & RAG Benchmark Metrics

### 🔬 Testing Methodology & Evaluation Framework (One-Line Summary)
> **Evaluated RAG performance across 20 synthetic campus queries measuring Context Precision, Factual Groundedness, and Out-of-Domain Guardrail Precision using an automated RAGAS-style evaluation framework, paired with empirical micro-performance execution timers.**

---

### 🏆 1. RAG Accuracy Benchmark Results (RAGAS Alignment)

| Evaluation Metric | Baseline Score | Post-Strategy 4 Tuning | RAGAS Alignment & Definition |
| :--- | :---: | :---: | :--- |
| **Context Retrieval Precision@5** | 90.0% | **95.0%** (19/20) | FAISS top-5 vector search returns exact ground-truth venue context. |
| **Intent Routing Precision** | 90.0% | **95.0%** (19/20) | Query intent classifier accuracy across Schedule, Rec, Peak, and Timing intents. |
| **Factual Groundedness Score** | 75.0% | **95.0%** (19/20) | Zero-hallucination rate of quoted figures against context evidence. |
| **Out-of-Domain Guardrail Precision** | 50.0% | **100.0%** (4/4) | Intercepts non-campus queries (*railway stations, recipes, flights*) before LLM inference. |
| **Overall RAG Benchmark Accuracy** | **75.0%** | **95.0%** (19/20) | **End-to-End System Accuracy across all 20 benchmark test cases.** |

---

### ⚡ 2. Verified System & Micro-Performance Benchmarks

| Component / Layer | Performance Metric | Measured Value | Practical Impact |
| :--- | :--- | :---: | :--- |
| **Layer 3 Personal Itinerary** | Personal Schedule Optimization | **1.83 ms** | Sub-2ms instantaneous itinerary generation. |
| **Prescriptive Impact** | Peak Congestion Time Saved | **160 mins / day** | Average wait time saved per student daily. |
| **Layer 3 Load Balancer** | Greedy Load-Balancing Speed | **620.05 ms** | Evaluates and load-balances 354 congested student profiles. |
| **Layer 3 Load Balancer** | Load-Balancing Success Rate | **86.4%** | Successfully resolves congestion hotspots below 85% threshold. |
| **Layer 2 Forecast Engine** | Single-Slot Prediction Latency | **476.74 ms** | Predicts 15-minute slot capacity across 12 venues. |
| **FAISS Vector Index** | Disk Load Time (480 Vectors) | **611.72 ms** | In-memory index initialization speed. |
| **FAISS Vector Search** | Top-5 Vector Search Latency | **145.91 ms** | Vector search speed across 480 dense embeddings. |

---

### 📂 File Locations
- JSON Data: [`rag_benchmark_results.json`](file:///c:/Users/yash3/Desktop/hackverse/benchmarks/rag_benchmark_results.json)
- Metric Measurement Script: [`scratch/measure_all_system_metrics.py`](file:///c:/Users/yash3/Desktop/hackverse/scratch/measure_all_system_metrics.py)
- RAG Test Suite: [`scratch/benchmark_rag_accuracy.py`](file:///c:/Users/yash3/Desktop/hackverse/scratch/benchmark_rag_accuracy.py)
