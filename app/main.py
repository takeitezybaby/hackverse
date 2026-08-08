from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
import os

from app.db.database import init_db
from app.api import ingest, routes
from data_gen.config import DEMO_NOW

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database & tables exist
    init_db()
    yield
    # Shutdown: Clean up resources if needed

app = FastAPI(
    title="Campus Digital Twin API",
    description="Process Mining & RAG-driven Digital Twin backend for Campus Congestion Copilot",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for local frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(ingest.router, prefix="/api")
app.include_router(routes.router, prefix="/api")

@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint returning server status, database state, and reference clock."""
    db_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'campus_twin.db')
    db_exists = os.path.exists(db_file)
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "demo_now": DEMO_NOW.isoformat(),
        "database_connected": db_exists,
        "database_file": db_file
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
