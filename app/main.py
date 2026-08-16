from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
import os

from app.db.database import init_db
from app.api import ingest, routes
from app.twin.simulation import sim_engine
from data_gen.config import DEMO_NOW

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database & tables exist and start live simulation
    init_db()
    sim_engine.start()
    yield
    sim_engine.stop()

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

@app.get("/forecast", tags=["Frontend Alias"])
def root_forecast_alias():
    """Alias for /api/forecast-frontend so React UI fetches work at root level."""
    return routes.get_frontend_formatted_forecast()

@app.get("/report/daily/{user_id}", tags=["Frontend Alias"])
def root_report_alias(user_id: str):
    """Alias for /api/report/daily/{user_id} so React UI fetches work at root level."""
    return routes.get_daily_user_report(user_id)

@app.post("/ask", tags=["Frontend Alias"])
def root_ask_alias(payload: routes.AskQueryRequest):
    """Alias for /api/ask so React UI chat works at root level."""
    return routes.ask_campus_copilot(payload)

@app.get("/allocate", tags=["Frontend Alias"])
def root_allocate_alias():
    """Alias for /api/allocate so load balancing metrics can be fetched at root level."""
    return routes.get_campus_wide_load_balancing()

@app.get("/api/sim/status", tags=["Simulation Engine"])
def get_sim_status():
    """Returns status of the live background simulation engine."""
    return sim_engine.get_status()

@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint returning server status, database state, and reference clock."""
    db_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'campus_twin.db')
    db_exists = os.path.exists(db_file)
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "simulation": sim_engine.get_status(),
        "database_connected": db_exists,
        "database_file": db_file
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
