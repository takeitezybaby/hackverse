import React, { useState } from 'react';
import { X, Code2, Database, Check, Copy, Server, Zap, ExternalLink, ArrowRight } from 'lucide-react';

interface ApiIntegrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  useLiveBackend: boolean;
  setUseLiveBackend: (val: boolean) => void;
}

export const ApiIntegrationModal: React.FC<ApiIntegrationModalProps> = ({
  isOpen,
  onClose,
  useLiveBackend,
  setUseLiveBackend,
}) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const pythonFastApiCode = `from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3

app = FastAPI(title="Campus Digital Twin Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/forecast")
def get_campus_forecast():
    # Queries SQLite database for live IoT telemetry & occupancy forecast
    conn = sqlite3.connect("campus_twin.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, occupancy, state_bucket, peak_hours FROM resources")
    rows = cursor.fetchall()
    return [{"id": r[0], "name": r[1], "currentOccupancy": r[2], "stateBucket": r[3], "peakHours": r[4]} for r in rows]

@app.get("/report/daily/{student_id}")
def get_daily_itinerary(student_id: str):
    # Generates load-balanced schedule recommendations for user
    return {
        "student_id": student_id,
        "load_balance_score": 92,
        "schedule": [
            {
                "id": "sched_workout",
                "category": "workout",
                "habit": {"time": "19:00", "activity": "Gym", "usualOccupancy": 95},
                "recommendation": {"time": "18:30", "activity": "Gym (Early Entry)", "predictedOccupancy": 60}
            }
        ]
    }`;

  const reactFetchCode = `// Fetching forecast & student itinerary from FastAPI backend
useEffect(() => {
  if (useLiveBackend) {
    Promise.all([
      fetch('http://localhost:8000/forecast').then(res => res.json()),
      fetch('http://localhost:8000/report/daily/u_042').then(res => res.json())
    ]).then(([forecastData, userData]) => {
      setResources(forecastData);
      setUserSchedule(userData.schedule);
    }).catch(err => {
      console.warn("Backend offline, falling back to local React state.", err);
    });
  }
}, [useLiveBackend]);`;

  const copyCode = () => {
    navigator.clipboard.writeText(pythonFastApiCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-fade-in">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl p-6 text-slate-200 relative">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors border border-slate-700"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center space-x-3 mb-6">
          <div className="p-3 rounded-2xl bg-indigo-950 border border-indigo-800 text-indigo-400">
            <Code2 className="w-6 h-6" />
          </div>
          <div>
            <span className="text-xs font-mono uppercase tracking-wider text-indigo-400 font-semibold block">
              FastAPI + SQLite Integration Guide
            </span>
            <h2 className="text-2xl font-bold text-white tracking-tight">
              Local Endpoint Binding Specs
            </h2>
          </div>
        </div>

        {/* Data Mode Switcher Toggle */}
        <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-xs font-bold text-slate-200">Data Source Mode</h3>
            <p className="text-[11px] text-slate-400">
              {useLiveBackend 
                ? 'Attempting native fetch() to http://localhost:8000 endpoints.'
                : 'Using structured local React state (FastAPI schema ready).'}
            </p>
          </div>

          <div className="flex items-center space-x-2 bg-slate-900 p-1 rounded-xl border border-slate-800 self-start sm:self-auto">
            <button
              onClick={() => setUseLiveBackend(false)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all ${
                !useLiveBackend 
                  ? 'bg-cyan-500 text-slate-950 font-bold shadow' 
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Mock State (Default)
            </button>
            <button
              onClick={() => setUseLiveBackend(true)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all ${
                useLiveBackend 
                  ? 'bg-indigo-500 text-white font-bold shadow' 
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              http://localhost:8000
            </button>
          </div>
        </div>

        {/* Endpoint Specs */}
        <div className="space-y-4 mb-6">
          <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
            Target FastAPI Endpoint Specs
          </h3>

          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-emerald-400 font-bold">GET /forecast</span>
              <span className="text-slate-500 text-[10px]">Returns list of ResourceItem objects</span>
            </div>
            <p className="text-slate-400 text-[11px]">
              Returns state buckets (green, yellow, red, purple), occupancy %, and trend arrows.
            </p>
          </div>

          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-emerald-400 font-bold">GET /report/daily/u_042</span>
              <span className="text-slate-500 text-[10px]">Returns DayScheduleEntry array</span>
            </div>
            <p className="text-slate-400 text-[11px]">
              Returns student habit vs load-balanced recommendations and time-saved metrics.
            </p>
          </div>
        </div>

        {/* Python FastAPI Code Box */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-300">FastAPI (Python) Reference Implementation:</span>
            <button
              onClick={copyCode}
              className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] border border-slate-700"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy Code'}</span>
            </button>
          </div>

          <pre className="p-4 rounded-2xl bg-slate-950 border border-slate-800 text-slate-300 font-mono text-[11px] overflow-x-auto leading-relaxed max-h-56">
            <code>{pythonFastApiCode}</code>
          </pre>
        </div>

        {/* React Fetch Hook */}
        <div className="mt-4 space-y-2">
          <span className="font-semibold text-slate-300 text-xs">React Fetch Switcher:</span>
          <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-cyan-300 font-mono text-[11px] overflow-x-auto leading-relaxed">
            <code>{reactFetchCode}</code>
          </pre>
        </div>

      </div>
    </div>
  );
};
