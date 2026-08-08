# Campus-as-a-Digital-Twin Copilot

## Quick Start (Every team member runs this first)

```bash
# 1. Clone the repo
git clone <repo-url>
cd hackverse

# 2. Create virtual environment
python -m venv venv

# 3. Activate venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Generate synthetic data
python data_gen/generate_all.py

# 6. Run the server
python -m app.main
```

## Project Structure

```
hackverse/
├── app/
│   ├── contracts.py          ← SHARED: All data structures (EVERYONE imports from here)
│   ├── main.py               ← FastAPI app entry point
│   ├── db/                   ← P1: Database setup + seeding
│   │   ├── __init__.py
│   │   ├── database.py
│   │   └── seed.py
│   ├── api/                  ← P1 (ingest) + P4 (routes)
│   │   ├── __init__.py
│   │   ├── ingest.py         ← P1: /ingest/* endpoints
│   │   └── routes.py         ← P4: /forecast/*, /report/*, /ask, /allocate
│   ├── twin/                 ← P2: Digital twin state model
│   │   ├── __init__.py
│   │   ├── state.py          ← Resource state management
│   │   └── forecast.py       ← Forecasting logic
│   ├── personalization/      ← P2: Personalization engine
│   │   ├── __init__.py
│   │   ├── profile.py        ← Usual-hours derivation
│   │   ├── congestion.py     ← Congestion matching
│   │   └── allocator.py      ← Greedy load-balanced allocation
│   ├── llm/                  ← P3: LLM integration
│   │   ├── __init__.py
│   │   ├── client.py         ← Ollama/Granite client
│   │   └── prompts.py        ← Prompt templates
│   └── rag/                  ← P3: RAG pipeline
│       ├── __init__.py
│       ├── embeddings.py     ← Embedding generation + FAISS indices
│       └── retriever.py      ← Similarity search per resource category
├── frontend/                 ← P4: Dashboard
│   ├── index.html
│   ├── css/
│   ├── js/
│   └── assets/
├── data_gen/                 ← P1: Synthetic data generators
├── data/                     ← Generated data (gitignored)
├── requirements.txt          ← Pinned dependencies
└── .gitignore
```

## Team Rules

### 1. NEVER edit another person's folder without asking
- P1 owns: `data_gen/`, `app/db/`, `app/api/ingest.py`
- P2 owns: `app/twin/`, `app/personalization/`
- P3 owns: `app/llm/`, `app/rag/`
- P4 owns: `frontend/`, `app/api/routes.py`
- SHARED (announce changes): `app/contracts.py`, `app/main.py`, `requirements.txt`

### 2. Always import from contracts.py
```python
# GOOD
from app.contracts import ResourceReading, StatusBucket, RESOURCES

# BAD - defining your own version
class ResourceReading:  # NO! Use the shared one
    ...
```

### 3. Git workflow
```bash
# Work on your own branch
git checkout -b p1/database-setup    # P1
git checkout -b p2/forecasting       # P2
git checkout -b p3/rag-pipeline      # P3
git checkout -b p4/dashboard         # P4

# Commit often
git add -A && git commit -m "P1: added SQLite schema"

# Before merging: pull main first
git checkout main && git pull
git checkout p1/database-setup && git merge main
# Fix conflicts, then push
git push origin p1/database-setup
# Create PR or merge to main
```

### 4. Integration checkpoints
- **Hour 8**: P1 + P2 integrate (data flows into forecast)
- **Hour 16**: P2 + P3 integrate (forecast feeds into RAG context)
- **Hour 22**: P3 + P4 integrate (LLM responses render in dashboard)
- **Hour 28**: Full integration test (all layers end-to-end)

### 5. If you change contracts.py
1. Message the group chat FIRST
2. Describe what changed and why
3. Everyone pulls and re-tests
